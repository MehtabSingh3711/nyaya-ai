import json
import os
from pathlib import Path
from sqlalchemy.orm import Session

from nyaya_ai.api.database import SessionLocal, ScanRecord
from nyaya_ai.contracts.scanner import scan_contract
from nyaya_ai.retrieval.embedder import Embedder
from nyaya_ai.retrieval.reranker import Reranker

def run_contract_scan_task(
    scan_id: str,
    temp_file_path: str,
    original_filename: str,
    embedder: Embedder,
    reranker: Reranker
):
    """Asynchronously scans the uploaded contract, computes findings, and saves to SQLite."""
    db = SessionLocal()
    try:
        # 1. Fetch the scan record
        scan_record = db.query(ScanRecord).filter(ScanRecord.scan_id == scan_id).first()
        if not scan_record:
            return

        # 2. Run the scanner
        path_obj = Path(temp_file_path)
        scan_result = scan_contract(
            file_path=path_obj,
            embedder=embedder,
            reranker=reranker
        )

        # 3. Calculate Overall Risk Level
        overall_risk = "none"
        if scan_result.findings:
            risk_levels = [f.risk_level for f in scan_result.findings]
            if "high" in risk_levels:
                overall_risk = "high"
            elif "medium" in risk_levels:
                overall_risk = "medium"
            elif "low" in risk_levels:
                overall_risk = "low"
        elif scan_result.status == "ocr_required":
            overall_risk = "none"  # Cannot analyze yet

        # 4. Update Database
        scan_record.status = "complete"
        scan_record.risk_level = overall_risk
        scan_record.clause_count = scan_result.total_clauses_scanned
        
        # Serialize the entire ContractScanResult object
        scan_record.results_json = json.dumps(scan_result.model_dump())

    except Exception as e:
        # Handle failures gracefully
        scan_record = db.query(ScanRecord).filter(ScanRecord.scan_id == scan_id).first()
        if scan_record:
            scan_record.status = "failed"
            # Store a dummy payload indicating failure
            scan_record.results_json = json.dumps({
                "contract_name": original_filename,
                "total_clauses_scanned": 0,
                "findings": [],
                "scan_confidence": 0.0,
                "status": "failed",
                "message": f"An error occurred during scanning: {str(e)}"
            })
    finally:
        # 5. Commit changes
        db.commit()
        db.close()
        
        # 6. Delete the temporary file
        if os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception:
                pass
