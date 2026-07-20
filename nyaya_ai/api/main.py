import json
import uuid
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel

from nyaya_ai.api.database import init_db, get_db, ChatSession, ChatMessage
from nyaya_ai.config import RERANK_CANDIDATES, FINAL_TOP_K
from nyaya_ai.llm.cascade import cascade_query
from nyaya_ai.retrieval.embedder import Embedder
from nyaya_ai.retrieval.reranker import Reranker
from nyaya_ai.store.qdrant import search
from nyaya_ai.schemas import CitedAnswer, Citation

app = FastAPI(
    title="Nyaya AI API",
    description="Backend API for Indian Legal Contract Intelligence & Statutory RAG",
    version="1.0.0"
)

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    init_db()
    # Preload models to memory
    app.state.embedder = Embedder()
    app.state.reranker = Reranker()

@app.get("/api/v1/health")
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
        
    return {
        "status": "ok",
        "database": db_status
    }

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    session_id: str
    answer: CitedAnswer

@app.post("/api/v1/chat", response_model=ChatResponse)
def chat_endpoint(request_data: ChatRequest, request: Request, db: Session = Depends(get_db)):
    # 1. Resolve Session ID
    session_id = request_data.session_id
    if not session_id:
        session_id = str(uuid.uuid4())
        # Auto-generate session title from first 50 chars of query
        title = request_data.message[:50] + "..." if len(request_data.message) > 50 else request_data.message
        session = ChatSession(session_id=session_id, title=title)
        db.add(session)
        db.commit()
    else:
        session = db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
        if not session:
            # If not found, create it anyway to prevent errors
            title = request_data.message[:50] + "..." if len(request_data.message) > 50 else request_data.message
            session = ChatSession(session_id=session_id, title=title)
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

    # 3. Retrieve & Rerank Chunks
    try:
        embedder = request.app.state.embedder
        reranker = request.app.state.reranker
        
        # Embed and Search
        query_hybrid = embedder.embed_query_hybrid(request_data.message)
        candidates = search(
            query_vector=query_hybrid.dense,
            sparse_vector=query_hybrid.sparse,
            top_k=RERANK_CANDIDATES
        )
        
        # Rerank
        if candidates:
            context_chunks = reranker.rerank(
                query=request_data.message,
                candidates=candidates,
                top_k=FINAL_TOP_K
            )
        else:
            context_chunks = []
    except Exception as e:
        # Fallback if retrieval fails (e.g. Qdrant unreachable or Mirror down in test mock environments)
        context_chunks = []

    # 4. Invoke LLM Cascade
    try:
        result = cascade_query(request_data.message, context_chunks)
    except Exception as e:
        # If cascade fails (e.g. invalid endpoint / api keys in testing), return a clean refusal instead of 500
        result = CitedAnswer(
            answer=f"Could not retrieve legal answer: {str(e)}",
            citations=[],
            confidence=0.0,
            can_answer=False
        )

    # 5. Save Assistant Message
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

import os
from nyaya_ai.api.database import ScanRecord
from nyaya_ai.api.tasks import run_contract_scan_task

TEMP_DIR = "temp_uploads"

@app.post("/api/v1/contracts/scan")
def scan_contract_endpoint(
    background_tasks: BackgroundTasks,
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # 1. Validate File Format
    filename = file.filename or "contract.pdf"
    ext = os.path.splitext(filename)[1].lower()
    if ext not in (".pdf", ".docx"):
        raise HTTPException(status_code=400, detail="Invalid file format. Only PDF and DOCX are supported.")

    # 2. Validate File Size (10MB limit)
    # We read in chunks to measure file size without loading everything into memory
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
        # Cleanup if validation failed
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
        contract_name=filename,
        status="processing",
        risk_level=None,
        clause_count=0
    )
    db.add(scan_record)
    db.commit()

    # 4. Trigger Asynchronous Scan
    background_tasks.add_task(
        run_contract_scan_task,
        scan_id=scan_id,
        temp_file_path=temp_file_path,
        original_filename=filename,
        embedder=request.app.state.embedder,
        reranker=request.app.state.reranker
    )

    return {
        "scan_id": scan_id,
        "status": "processing"
    }

@app.get("/api/v1/contracts/scan/{scan_id}")
def get_scan_result_endpoint(scan_id: str, db: Session = Depends(get_db)):
    scan_record = db.query(ScanRecord).filter(ScanRecord.scan_id == scan_id).first()
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

    if scan_record.status in ("complete", "failed") and scan_record.results_json:
        try:
            response_data["results"] = json.loads(scan_record.results_json)
        except Exception:
            pass

    return response_data

from fastapi.responses import Response
from nyaya_ai.api.exporter import generate_pdf_report

@app.get("/api/v1/contracts/scan/{scan_id}/export")
def export_scan_report_endpoint(scan_id: str, db: Session = Depends(get_db)):
    scan_record = db.query(ScanRecord).filter(ScanRecord.scan_id == scan_id).first()
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

@app.get("/api/v1/contracts/scans")
def list_scans_endpoint(db: Session = Depends(get_db)):
    scans = db.query(ScanRecord).order_by(ScanRecord.scan_date.desc()).all()
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
def get_dashboard_stats_endpoint(db: Session = Depends(get_db)):
    # 1. Total Scanned
    total_scanned = db.query(ScanRecord).filter(ScanRecord.status == "complete").count()
    
    # 2. Total Risks
    complete_scans = db.query(ScanRecord).filter(ScanRecord.status == "complete").all()
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
def list_chat_sessions_endpoint(db: Session = Depends(get_db)):
    sessions = db.query(ChatSession).order_by(ChatSession.created_at.desc()).all()
    results = []
    for s in sessions:
        results.append({
            "session_id": s.session_id,
            "title": s.title,
            "created_at": s.created_at.isoformat()
        })
    return results

@app.get("/api/v1/chat/sessions/{session_id}")
def get_chat_session_endpoint(session_id: str, db: Session = Depends(get_db)):
    session = db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
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
def delete_chat_session_endpoint(session_id: str, db: Session = Depends(get_db)):
    session = db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found.")
        
    # Delete associated messages first
    db.query(ChatMessage).filter(ChatMessage.session_id == session_id).delete()
    db.delete(session)
    db.commit()
    
    return {"status": "deleted"}





