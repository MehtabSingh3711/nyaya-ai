import json
import os
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from nyaya_ai.api.database import Base, get_db, ScanRecord, ChatSession, ChatMessage
from nyaya_ai.schemas import CitedAnswer, Citation, ContractScanResult, RiskFinding

# We must patch the Embedder and Reranker during import or startup
# to prevent it from trying to download BGE-M3 (2.3GB) during test initialization.
with patch("nyaya_ai.retrieval.embedder.Embedder") as mock_embedder_class, \
     patch("nyaya_ai.retrieval.reranker.Reranker") as mock_reranker_class:
    
    # Initialize mock instances
    mock_embedder = MagicMock()
    mock_reranker = MagicMock()
    
    mock_embedder_class.return_value = mock_embedder
    mock_reranker_class.return_value = mock_reranker

    from nyaya_ai.api.main import app

from sqlalchemy.pool import StaticPool

# Setup test database engine (in-memory SQLite shared across connections)
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

from nyaya_ai.api.main import get_current_user
from nyaya_ai.api.database import User

def override_get_current_user():
    return User(user_id=None, username="testuser", hashed_password="mocked_password")

app.dependency_overrides[get_current_user] = override_get_current_user


@pytest.fixture(autouse=True)
def setup_database():
    """Initializes in-memory database schema before each test, and drops it after."""
    Base.metadata.create_all(bind=engine)
    # Manually configure the state objects for tests
    app.state.embedder = MagicMock()
    app.state.reranker = MagicMock()
    yield
    Base.metadata.drop_all(bind=engine)


def test_health_endpoint():
    """Test that health check connects to database and returns ok."""
    client = TestClient(app)
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "healthy"}


@patch("nyaya_ai.api.main.search")
@patch("nyaya_ai.api.main.cascade_query")
def test_chat_endpoint(mock_cascade, mock_search):
    """Test that /chat resolving, embedding, and cascade functions work, saving message history."""
    client = TestClient(app)

    # 1. Setup mocks
    mock_search.return_value = [{"act_name": "Indian Contract Act, 1872", "section_number": "27", "text": "Void clause"}]
    mock_cascade.return_value = CitedAnswer(
        answer="Agreement in restraint of trade is void.",
        citations=[
            Citation(
                source_type="statute",
                act_name="Indian Contract Act, 1872",
                section="27",
                quote="Agreement in restraint of trade is void."
            )
        ],
        confidence=0.95,
        can_answer=True
    )

    # 2. Make request
    payload = {"message": "Is non-compete valid under ICA §27?"}
    response = client.post("/api/v1/chat", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert data["answer"]["can_answer"] is True
    assert data["answer"]["answer"] == "Agreement in restraint of trade is void."
    assert len(data["answer"]["citations"]) == 1
    
    # 3. Verify SQLite persistence
    db = TestingSessionLocal()
    session_id = data["session_id"]
    chat_session = db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
    assert chat_session is not None
    assert chat_session.title.startswith("Is non-compete valid")
    
    messages = db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at).all()
    assert len(messages) == 2
    assert messages[0].role == "user"
    assert messages[0].content == "Is non-compete valid under ICA §27?"
    assert messages[1].role == "assistant"
    assert messages[1].content == "Agreement in restraint of trade is void."
    db.close()


def test_contracts_scan_invalid_inputs():
    """Test that size limit (>10MB) and format validations are enforced on upload."""
    client = TestClient(app)

    # Invalid file extension
    files = {"file": ("test.txt", b"Hello", "text/plain")}
    response = client.post("/api/v1/contracts/scan", files=files)
    assert response.status_code == 400
    assert "supported" in response.json()["detail"]

    # File too large (11MB)
    large_payload = b"0" * (11 * 1024 * 1024)
    files = {"file": ("test.pdf", large_payload, "application/pdf")}
    response = client.post("/api/v1/contracts/scan", files=files)
    assert response.status_code == 413
    assert "10MB limit" in response.json()["detail"]


@patch("nyaya_ai.api.main.run_contract_scan_task")
def test_contracts_scan_processing_and_status(mock_run_task):
    """Test starting a contract scan and checking its status through database processing lifecycle."""
    client = TestClient(app)

    # 1. Upload valid document
    files = {"file": ("employment_contract.pdf", b"Dummy PDF bytes", "application/pdf")}
    response = client.post("/api/v1/contracts/scan", files=files)
    assert response.status_code == 200
    scan_data = response.json()
    assert "scan_id" in scan_data
    assert scan_data["status"] == "processing"
    
    # Check that task was scheduled
    scan_id = scan_data["scan_id"]
    mock_run_task.assert_called_once()
    
    # 2. Check status (should be processing in DB)
    response = client.get(f"/api/v1/contracts/scan/{scan_id}")
    assert response.status_code == 200
    status_data = response.json()
    assert status_data["status"] == "processing"
    assert status_data["results"] is None

    # 3. Simulate background task completion
    db = TestingSessionLocal()
    scan_rec = db.query(ScanRecord).filter(ScanRecord.scan_id == scan_id).first()
    scan_rec.status = "complete"
    scan_rec.risk_level = "high"
    scan_rec.clause_count = 1
    scan_rec.results_json = json.dumps({
        "contract_name": "employment_contract.pdf",
        "total_clauses_scanned": 1,
        "findings": [
            {
                "clause_number": "3",
                "clause_text": "No working anywhere else for 5 years",
                "page": 1,
                "clause_type": "non_compete",
                "risk_level": "high",
                "conflicting_act": "Indian Contract Act 1872",
                "conflicting_section": "27",
                "conflicting_law_quote": "restraint of trade is void",
                "explanation": "Void restriction",
                "recommended_action": "Negotiate",
                "confidence": 0.98
            }
        ],
        "scan_confidence": 0.98,
        "status": "risks_found",
        "message": "Found high risk restraint of trade"
    })
    db.commit()
    db.close()

    # 4. Check completed status from API
    response = client.get(f"/api/v1/contracts/scan/{scan_id}")
    assert response.status_code == 200
    complete_data = response.json()
    assert complete_data["status"] == "complete"
    assert complete_data["risk_level"] == "high"
    assert complete_data["clause_count"] == 1
    assert complete_data["results"]["status"] == "risks_found"
    assert len(complete_data["results"]["findings"]) == 1


def test_dashboard_stats_and_history():
    """Test list scans and telemetry endpoints populate aggregate metrics from SQLite records."""
    client = TestClient(app)

    db = TestingSessionLocal()
    # Create two records: one complete, one processing
    scan1 = ScanRecord(
        scan_id="s1",
        contract_name="nda.pdf",
        status="complete",
        risk_level="medium",
        clause_count=5,
        results_json=json.dumps({
            "findings": [{"risk_level": "medium"}, {"risk_level": "low"}]
        })
    )
    scan2 = ScanRecord(
        scan_id="s2",
        contract_name="vendor.docx",
        status="processing"
    )
    db.add_all([scan1, scan2])
    db.commit()
    db.close()

    # 1. Test scans list
    response = client.get("/api/v1/contracts/scans")
    assert response.status_code == 200
    scans_list = response.json()
    assert len(scans_list) == 2
    assert scans_list[0]["contract_name"] in ("nda.pdf", "vendor.docx")

    # 2. Test dashboard telemetry aggregates
    response = client.get("/api/v1/dashboard/stats")
    assert response.status_code == 200
    stats = response.json()
    assert stats["total_contracts_scanned"] == 1  # only completed scans
    assert stats["total_risks_identified"] == 2   # count of items in findings list
    assert stats["total_api_cost"] == "₹0.00"


def test_scan_pdf_export_errors_and_download():
    """Test generating compliance PDF downloads and matching content-type."""
    client = TestClient(app)

    # 1. 404 on invalid ID
    response = client.get("/api/v1/contracts/scan/invalid_id/export")
    assert response.status_code == 404

    # 2. 400 if still processing
    db = TestingSessionLocal()
    scan = ScanRecord(
        scan_id="s_processing",
        contract_name="draft.pdf",
        status="processing"
    )
    db.add(scan)
    db.commit()
    db.close()
    
    response = client.get("/api/v1/contracts/scan/s_processing/export")
    assert response.status_code == 400
    assert "still processing" in response.json()["detail"]

    # 3. Successful PDF download
    db = TestingSessionLocal()
    scan_complete = ScanRecord(
        scan_id="s_complete",
        contract_name="final_agreement.pdf",
        status="complete",
        risk_level="high",
        clause_count=1,
        results_json=json.dumps({
            "contract_name": "final_agreement.pdf",
            "findings": [
                {
                    "clause_number": "1",
                    "clause_text": "Non-compete",
                    "page": 1,
                    "clause_type": "non_compete",
                    "risk_level": "high",
                    "conflicting_act": "Indian Contract Act",
                    "conflicting_section": "27",
                    "conflicting_law_quote": "void",
                    "explanation": "test explanation",
                    "recommended_action": "test recommendation"
                }
            ],
            "status": "risks_found",
            "message": "Audit findings"
        })
    )
    db.add(scan_complete)
    db.commit()
    db.close()

    response = client.get("/api/v1/contracts/scan/s_complete/export")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment; filename=" in response.headers["content-disposition"]
    # PDF starts with %PDF magic signature bytes
    assert response.content.startswith(b"%PDF")


def test_chat_sessions_crud():
    """Test listing, retrieving, and deleting historical chat sessions."""
    client = TestClient(app)

    db = TestingSessionLocal()
    # Create a chat session with two messages
    session = ChatSession(session_id="session_123", title="Non-compete validity")
    msg1 = ChatMessage(
        message_id="m1",
        session_id="session_123",
        role="user",
        content="Is non-compete valid?"
    )
    msg2 = ChatMessage(
        message_id="m2",
        session_id="session_123",
        role="assistant",
        content="No, under Section 27 it is void.",
        citations_json=json.dumps([{
            "act_name": "Indian Contract Act",
            "section": "27",
            "quote": "void"
        }])
    )
    db.add_all([session, msg1, msg2])
    db.commit()
    db.close()

    # 1. Test listing sessions
    response = client.get("/api/v1/chat/sessions")
    assert response.status_code == 200
    sessions = response.json()
    assert len(sessions) == 1
    assert sessions[0]["session_id"] == "session_123"
    assert sessions[0]["title"] == "Non-compete validity"

    # 2. Test retrieving session detail
    response = client.get("/api/v1/chat/sessions/session_123")
    assert response.status_code == 200
    detail = response.json()
    assert detail["session_id"] == "session_123"
    assert detail["title"] == "Non-compete validity"
    assert len(detail["messages"]) == 2
    assert detail["messages"][0]["role"] == "user"
    assert detail["messages"][1]["role"] == "assistant"
    assert len(detail["messages"][1]["citations"]) == 1
    assert detail["messages"][1]["citations"][0]["act_name"] == "Indian Contract Act"

    # 3. Test deleting session
    response = client.delete("/api/v1/chat/sessions/session_123")
    assert response.status_code == 200
    assert response.json() == {"status": "deleted"}

    # Verify deletion from database
    db = TestingSessionLocal()
    assert db.query(ChatSession).filter(ChatSession.session_id == "session_123").first() is None
    assert db.query(ChatMessage).filter(ChatMessage.session_id == "session_123").count() == 0
    db.close()


def test_auth_signup_signin():
    """Test user registration, duplicate user prevention, and signin token validation."""
    client = TestClient(app)

    # 1. Sign up a new user
    signup_payload = {"username": "testuser1", "password": "securepassword"}
    response = client.post("/api/v1/auth/signup", json=signup_payload)
    assert response.status_code == 200
    signup_data = response.json()
    assert "access_token" in signup_data
    assert signup_data["username"] == "testuser1"

    # 2. Prevent duplicate user signup
    response = client.post("/api/v1/auth/signup", json=signup_payload)
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"]

    # 3. Sign in successfully
    response = client.post("/api/v1/auth/signin", json=signup_payload)
    assert response.status_code == 200
    signin_data = response.json()
    assert "access_token" in signin_data
    assert signin_data["username"] == "testuser1"

    # 4. Sign in with invalid password
    invalid_signin = {"username": "testuser1", "password": "wrongpassword"}
    response = client.post("/api/v1/auth/signin", json=invalid_signin)
    assert response.status_code == 401
    assert "Invalid username" in response.json()["detail"]