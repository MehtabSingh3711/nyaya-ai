import json
import uuid
import os
import hashlib
import jwt
import bcrypt
import redis
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, List
from pydantic import BaseModel

from nyaya_ai.api.database import init_db, get_db, ChatSession, ChatMessage, User
from nyaya_ai.config import RERANK_CANDIDATES, FINAL_TOP_K
from nyaya_ai.llm.cascade import cascade_query
from nyaya_ai.retrieval.embedder import Embedder
from nyaya_ai.retrieval.reranker import Reranker
from nyaya_ai.store.qdrant import search
from nyaya_ai.schemas import CitedAnswer, Citation
# JWT Authentication Config
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    import warnings
    SECRET_KEY = "nyaya_secret_key_fallback_dev_only"
    warnings.warn(
        "JWT_SECRET_KEY environment variable not set. Falling back to temporary dev key.",
        RuntimeWarning
    )
ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=False)


# Redis Cache Config
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = None
try:
    redis_client = redis.from_url(REDIS_URL, socket_timeout=2.0)
    redis_client.ping()
except Exception:
    redis_client = None
    print("[Warning] Redis connection failed. Caching is disabled.")

app = FastAPI(
    title="Nyaya AI API",
    description="Backend API for Indian Legal Contract Intelligence & Statutory RAG",
    version="1.0.0"
)

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for development flexibility
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth dependency helper
def get_current_user(token: Optional[str] = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    if not token:
        raise HTTPException(status_code=401, detail="Authentication credentials were not provided.")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication token.")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials.")

    user = db.query(User).filter(User.user_id == user_id).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User account not found.")
    return user


@app.on_event("startup")
def startup_event():
    init_db()
    # Preload models to memory
    app.state.embedder = Embedder()
    app.state.reranker = Reranker()

class AuthRequest(BaseModel):
    username: str
    password: str

@app.post("/api/v1/auth/signup")
def signup_endpoint(request_data: AuthRequest, db: Session = Depends(get_db)):
    # 1. Check if user already exists
    existing = db.query(User).filter(User.username == request_data.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already registered.")

    # 2. Hash password
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(request_data.password.encode("utf-8"), salt).decode("utf-8")

    # 3. Create User
    user_id = str(uuid.uuid4())
    user = User(user_id=user_id, username=request_data.username, hashed_password=hashed)
    db.add(user)
    db.commit()

    # 4. Generate JWT Token
    token = jwt.encode({"sub": user_id}, SECRET_KEY, algorithm=ALGORITHM)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user_id,
        "username": user.username,
    }

@app.post("/api/v1/auth/signin")
def signin_endpoint(request_data: AuthRequest, db: Session = Depends(get_db)):
    # 1. Find User
    user = db.query(User).filter(User.username == request_data.username).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    # 2. Validate Password
    if not bcrypt.checkpw(request_data.password.encode("utf-8"), user.hashed_password.encode("utf-8")):
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    # 3. Generate JWT Token
    token = jwt.encode({"sub": user.user_id}, SECRET_KEY, algorithm=ALGORITHM)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user.user_id,
        "username": user.username,
    }

@app.post("/api/v1/auth/token")
def token_endpoint(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # 1. Find User
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    # 2. Validate Password
    if not bcrypt.checkpw(form_data.password.encode("utf-8"), user.hashed_password.encode("utf-8")):
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    # 3. Generate JWT Token
    token = jwt.encode({"sub": user.user_id}, SECRET_KEY, algorithm=ALGORITHM)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user.user_id,
        "username": user.username,
    }

@app.get("/api/v1/health")


def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
        
    return {
        "status": "ok",
        "database": db_status
    }

def expand_legal_query(query: str) -> str:
    """Enhance query with canonical Indian legal terminology for higher RAG retrieval recall."""
    query_lower = query.lower()
    expansions = []
    if "non-compete" in query_lower or "non compete" in query_lower or "solicitation" in query_lower:
        expansions.append("restraint of trade Section 27 Indian Contract Act 1872")
    if "data" in query_lower or "privacy" in query_lower or "breach" in query_lower:
        expansions.append("sensitive personal data Section 43A Information Technology Act 2000")
    if "cheque" in query_lower or "bounce" in query_lower:
        expansions.append("dishonour of cheque Section 138 Negotiable Instruments Act 1881")
    if "msme" in query_lower or "45 days" in query_lower:
        expansions.append("payment of dues Section 15 Section 16 MSME Development Act 2006")
    if "penalty" in query_lower or "liquidated" in query_lower:
        expansions.append("compensation for breach of contract Section 74 Indian Contract Act 1872")
    
    if expansions:
        return f"{query} {' '.join(expansions)}"
    return query

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    session_id: str
    answer: CitedAnswer

@app.post("/api/v1/chat", response_model=ChatResponse)
def chat_endpoint(
    request_data: ChatRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Resolve Session ID and verify user ownership
    session_id = request_data.session_id
    if not session_id:
        session_id = str(uuid.uuid4())
        title = request_data.message[:50] + "..." if len(request_data.message) > 50 else request_data.message
        session = ChatSession(session_id=session_id, user_id=current_user.user_id, title=title)
        db.add(session)
        db.commit()
    else:
        session = db.query(ChatSession).filter(
            ChatSession.session_id == session_id,
            ChatSession.user_id == current_user.user_id
        ).first()
        if not session:
            title = request_data.message[:50] + "..." if len(request_data.message) > 50 else request_data.message
            session = ChatSession(session_id=session_id, user_id=current_user.user_id, title=title)
            db.add(session)
            db.commit()

    # 2. Save User Message
    user_msg = ChatMessage(
        message_id=str(uuid.uuid4()),
        session_id=session_id,
        role="user",
        content=request_data.message
    )
    db.add(user_msg)
    db.commit()

    # 3. Check Redis Cache
    cache_key = None
    if redis_client:
        try:
            query_hash = hashlib.sha256(request_data.message.encode("utf-8")).hexdigest()
            cache_key = f"chat_cache:{current_user.user_id}:{query_hash}"
            cached_val = redis_client.get(cache_key)
            if cached_val:
                # Cache Hit!
                print(f"[Cache] HIT for key: {cache_key}")
                result_dict = json.loads(cached_val)
                result = CitedAnswer.model_validate(result_dict)

                # Save assistant response to DB
                citations_data = [c.model_dump() for c in result.citations]
                assistant_msg = ChatMessage(
                    message_id=str(uuid.uuid4()),
                    session_id=session_id,
                    role="assistant",
                    content=result.answer,
                    citations_json=json.dumps(citations_data)
                )
                db.add(assistant_msg)
                db.commit()

                return ChatResponse(session_id=session_id, answer=result)
            else:
                print(f"[Cache] MISS for key: {cache_key}")
        except Exception as e:
            print(f"[Cache] Error checking cache: {e}")

    # 4. Retrieve & Rerank Chunks (Cache Miss)
    try:
        embedder = request.app.state.embedder
        reranker = request.app.state.reranker
        
        # Expand query with canonical Indian legal terminology for higher RAG recall
        search_query = expand_legal_query(request_data.message)

        # Embed and Search
        query_hybrid = embedder.embed_query_hybrid(search_query)
        candidates = search(
            query_vector=query_hybrid.dense,
            sparse_vector=query_hybrid.sparse,
            top_k=RERANK_CANDIDATES
        )
        
        # Rerank against original message for accuracy
        if candidates:
            context_chunks = reranker.rerank(
                query=request_data.message,
                candidates=candidates,
                top_k=FINAL_TOP_K
            )
        else:
            context_chunks = []
    except Exception:
        context_chunks = []

    # 5. Invoke LLM Cascade
    try:
        result = cascade_query(request_data.message, context_chunks)
    except Exception as e:
        result = CitedAnswer(
            answer=f"Could not retrieve legal answer: {str(e)}",
            citations=[],
            confidence=0.0,
            can_answer=False
        )

    # 6. Save Assistant Message
    citations_data = [c.model_dump() for c in result.citations]
    assistant_msg = ChatMessage(
        message_id=str(uuid.uuid4()),
        session_id=session_id,
        role="assistant",
        content=result.answer,
        citations_json=json.dumps(citations_data)
    )
    db.add(assistant_msg)
    db.commit()

    # 7. Write to Redis Cache
    if redis_client and cache_key:
        try:
            # Cache successful answers for 2 hours, refusals for 5 minutes (300 seconds)
            ttl = 7200 if result.can_answer else 300
            redis_client.setex(cache_key, ttl, result.model_dump_json())
            print(f"[Cache] Saved key {cache_key} with TTL={ttl}s")
        except Exception as e:
            print(f"[Cache] Error writing to cache: {e}")

    return ChatResponse(session_id=session_id, answer=result)



import os
from nyaya_ai.api.database import ScanRecord
from nyaya_ai.api.tasks import run_contract_scan_task, run_contract_scan_task_local

TEMP_DIR = "temp_uploads"

@app.post("/api/v1/contracts/scan")
def scan_contract_endpoint(
    background_tasks: BackgroundTasks,
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Validate File Format
    filename = file.filename or "contract.pdf"
    ext = os.path.splitext(filename)[1].lower()
    if ext not in (".pdf", ".docx"):
        raise HTTPException(status_code=400, detail="Invalid file format. Only PDF and DOCX are supported.")

    # 2. Validate File Size (10MB limit)
    os.makedirs(TEMP_DIR, exist_ok=True)
    scan_id = str(uuid.uuid4())
    temp_file_path = os.path.join(TEMP_DIR, f"{scan_id}{ext}")
    
    total_size = 0
    max_size = 10 * 1024 * 1024  # 10MB
    
    try:
        with open(temp_file_path, "wb") as buffer:
            while chunk := file.file.read(8192):
                total_size += len(chunk)
                if total_size > max_size:
                    raise HTTPException(status_code=413, detail="File size exceeds the 10MB limit.")
                buffer.write(chunk)
    except HTTPException:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        raise
    except Exception as e:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        raise HTTPException(status_code=500, detail=f"File save error: {str(e)}")

    # 3. Create Scan Record in Database
    scan_record = ScanRecord(
        scan_id=scan_id,
        user_id=current_user.user_id,
        contract_name=filename,
        status="processing",
        risk_level=None,
        clause_count=0
    )
    db.add(scan_record)
    db.commit()

    # 4. Trigger Asynchronous Scan directly via FastAPI BackgroundTasks (Celery bypassed for simplicity & speed)
    background_tasks.add_task(
        run_contract_scan_task_local,
        scan_id=scan_id,
        temp_file_path=temp_file_path,
        original_filename=filename,
        user_id=current_user.user_id,
        embedder=request.app.state.embedder,
        reranker=request.app.state.reranker,
    )

    return {
        "scan_id": scan_id,
        "status": "processing"
    }

@app.get("/api/v1/contracts/scan/{scan_id}")
def get_scan_result_endpoint(
    scan_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    scan_record = db.query(ScanRecord).filter(
        ScanRecord.scan_id == scan_id,
        ScanRecord.user_id == current_user.user_id
    ).first()
    if not scan_record:
        raise HTTPException(status_code=404, detail="Scan record not found.")

    response_data = {
        "scan_id": scan_record.scan_id,
        "status": scan_record.status,
        "risk_level": scan_record.risk_level,
        "clause_count": scan_record.clause_count,
        "scan_date": scan_record.scan_date.isoformat(),
        "results": None
    }

    if scan_record.status in ("complete", "failed", "processing") and scan_record.results_json:
        try:
            response_data["results"] = json.loads(scan_record.results_json)
        except Exception:
            pass

    return response_data

from fastapi.responses import Response
from nyaya_ai.api.exporter import generate_pdf_report

@app.get("/api/v1/contracts/scan/{scan_id}/export")
def export_scan_report_endpoint(
    scan_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    scan_record = db.query(ScanRecord).filter(
        ScanRecord.scan_id == scan_id,
        ScanRecord.user_id == current_user.user_id
    ).first()
    if not scan_record:
        raise HTTPException(status_code=404, detail="Scan record not found.")

    if scan_record.status == "processing":
        raise HTTPException(status_code=400, detail="Compliance report is still processing. Please try again shortly.")
        
    try:
        pdf_bytes = generate_pdf_report(scan_record)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF report: {str(e)}")

    safe_filename = f"nyaya_compliance_report_{scan_id}.pdf"
    headers = {
        "Content-Disposition": f'attachment; filename="{safe_filename}"'
    }
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers=headers
    )

@app.delete("/api/v1/contracts/scan/{scan_id}")
def delete_scan_endpoint(
    scan_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    scan_record = db.query(ScanRecord).filter(
        ScanRecord.scan_id == scan_id,
        ScanRecord.user_id == current_user.user_id
    ).first()
    if not scan_record:
        raise HTTPException(status_code=404, detail="Scan record not found.")

    # 1. Delete record from SQLite database
    db.delete(scan_record)
    db.commit()

    # 2. Delete contract vector embeddings from Qdrant Cloud
    try:
        from nyaya_ai.store.qdrant import delete_contract_vectors
        delete_contract_vectors(contract_id=scan_id)
    except Exception as qdrant_err:
        print(f"[Warning] Failed to delete contract vectors from Qdrant: {qdrant_err}")

    return {"status": "success", "message": f"Scan record {scan_id} and associated vector embeddings deleted successfully."}

@app.get("/api/v1/contracts/scans")
def list_scans_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    scans = db.query(ScanRecord).filter(
        ScanRecord.user_id == current_user.user_id
    ).order_by(ScanRecord.scan_date.desc()).all()
    results = []
    for s in scans:
        results.append({
            "scan_id": s.scan_id,
            "contract_name": s.contract_name,
            "clause_count": s.clause_count,
            "status": s.status,
            "risk_level": s.risk_level,
            "scan_date": s.scan_date.isoformat()
        })
    return results

@app.get("/api/v1/dashboard/stats")
def get_dashboard_stats_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Total Scanned
    total_scanned = db.query(ScanRecord).filter(
        ScanRecord.status == "complete",
        ScanRecord.user_id == current_user.user_id
    ).count()
    
    # 2. Total Risks
    complete_scans = db.query(ScanRecord).filter(
        ScanRecord.status == "complete",
        ScanRecord.user_id == current_user.user_id
    ).all()
    total_risks = 0
    for s in complete_scans:
        if s.results_json:
            try:
                data = json.loads(s.results_json)
                total_risks += len(data.get("findings", []))
            except Exception:
                pass
                
    return {
        "total_contracts_scanned": total_scanned,
        "total_risks_identified": total_risks,
        "total_api_cost": "₹0.00"
    }

@app.get("/api/v1/chat/sessions")
def list_chat_sessions_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    sessions = db.query(ChatSession).filter(
        ChatSession.user_id == current_user.user_id
    ).order_by(ChatSession.created_at.desc()).all()
    results = []
    for s in sessions:
        results.append({
            "session_id": s.session_id,
            "title": s.title,
            "created_at": s.created_at.isoformat()
        })
    return results

@app.get("/api/v1/chat/sessions/{session_id}")
def get_chat_session_endpoint(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    session = db.query(ChatSession).filter(
        ChatSession.session_id == session_id,
        ChatSession.user_id == current_user.user_id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found.")
        
    messages = db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at.asc()).all()
    
    msg_list = []
    for m in messages:
        citations = []
        if m.citations_json:
            try:
                citations = json.loads(m.citations_json)
            except Exception:
                pass
        msg_list.append({
            "message_id": m.message_id,
            "role": m.role,
            "content": m.content,
            "citations": citations,
            "created_at": m.created_at.isoformat()
        })
        
    return {
        "session_id": session.session_id,
        "title": session.title,
        "messages": msg_list
    }

@app.delete("/api/v1/chat/sessions/{session_id}")
def delete_chat_session_endpoint(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    session = db.query(ChatSession).filter(
        ChatSession.session_id == session_id,
        ChatSession.user_id == current_user.user_id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found.")
        
    # Delete associated messages first
    db.query(ChatMessage).filter(ChatMessage.session_id == session_id).delete()
    db.delete(session)
    db.commit()
    
    return {"status": "deleted"}
