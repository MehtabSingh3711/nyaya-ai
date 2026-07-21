import json
import os
from pathlib import Path
from sqlalchemy.orm import Session
from celery import Celery

from nyaya_ai.api.database import SessionLocal, ScanRecord
from nyaya_ai.contracts.scanner import scan_contract
from nyaya_ai.retrieval.embedder import Embedder
from nyaya_ai.retrieval.reranker import Reranker

# Initialize Celery app
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
celery_app = Celery("nyaya_tasks", broker=REDIS_URL, backend=REDIS_URL)

# Worker singletons to avoid reloading 2GB models on each task call
_celery_embedder = None
_celery_reranker = None

def get_celery_models():
    """Lazy initialize embedder and reranker models in the Celery worker process."""
    global _celery_embedder, _celery_reranker
    if _celery_embedder is None:
        _celery_embedder = Embedder()
    if _celery_reranker is None:
        _celery_reranker = Reranker()
    return _celery_embedder, _celery_reranker


@celery_app.task
def run_contract_scan_task(
    scan_id: str,
    temp_file_path: str,
    original_filename: str,
    user_id: str | None = None,
):
    """Asynchronously scans the uploaded contract via Celery worker."""
    db = SessionLocal()
    try:
        # 1. Fetch the scan record
        scan_record = db.query(ScanRecord).filter(ScanRecord.scan_id == scan_id).first()
        if not scan_record:
            return

        # 2. Get worker preloaded models
        embedder, reranker = get_celery_models()

        # 3. Run the scanner
        path_obj = Path(temp_file_path)
        scan_result = scan_contract(
            file_path=path_obj,
            embedder=embedder,
            reranker=reranker,
            user_id=user_id,
        )

        # 4. Calculate Overall Risk Level
        overall_risk = "none"
        if scan_result.findings:
            risk_levels = [f.risk_level for f in scan_result.findings]
            if "high" in risk_levels:
                overall_risk = "high"
            elif "medium" in risk_levels:
                overall_risk = "medium"
            elif "low" in risk_levels:
                overall_risk = "low"

        # 5. Update Database
        scan_record.status = "complete"
        scan_record.risk_level = overall_risk
        scan_record.clause_count = scan_result.total_clauses_scanned
        scan_record.results_json = json.dumps(scan_result.model_dump())

    except Exception as e:
        scan_record = db.query(ScanRecord).filter(ScanRecord.scan_id == scan_id).first()
        if scan_record:
            scan_record.status = "failed"
            scan_record.results_json = json.dumps({
                "contract_name": original_filename,
                "total_clauses_scanned": 0,
                "findings": [],
                "scan_confidence": 0.0,
                "status": "failed",
                "message": f"An error occurred during scanning: {str(e)}"
            })
    finally:
        db.commit()
        db.close()
        
        # Delete temporary file
        if os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception:
                pass


def run_contract_scan_task_local(
    scan_id: str,
    temp_file_path: str,
    original_filename: str,
    user_id: str | None = None,
    embedder: Embedder | None = None,
    reranker: Reranker | None = None,
):
    """Fallback local background thread runner when Celery is offline."""
    db = SessionLocal()
    try:
        scan_record = db.query(ScanRecord).filter(ScanRecord.scan_id == scan_id).first()
        if not scan_record:
            return

        if not embedder:
            embedder = Embedder()
        if not reranker:
            reranker = Reranker()

        path_obj = Path(temp_file_path)
        scan_result = scan_contract(
            file_path=path_obj,
            embedder=embedder,
            reranker=reranker,
            user_id=user_id,
        )

        overall_risk = "none"
        if scan_result.findings:
            risk_levels = [f.risk_level for f in scan_result.findings]
            if "high" in risk_levels:
                overall_risk = "high"
            elif "medium" in risk_levels:
                overall_risk = "medium"
            elif "low" in risk_levels:
                overall_risk = "low"

        scan_record.status = "complete"
        scan_record.risk_level = overall_risk
        scan_record.clause_count = scan_result.total_clauses_scanned
        scan_record.results_json = json.dumps(scan_result.model_dump())

    except Exception as e:
        scan_record = db.query(ScanRecord).filter(ScanRecord.scan_id == scan_id).first()
        if scan_record:
            scan_record.status = "failed"
            scan_record.results_json = json.dumps({
                "contract_name": original_filename,
                "total_clauses_scanned": 0,
                "findings": [],
                "scan_confidence": 0.0,
                "status": "failed",
                "message": f"An error occurred during scanning: {str(e)}"
            })
    finally:
        db.commit()
        db.close()

        if os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception:
                pass

