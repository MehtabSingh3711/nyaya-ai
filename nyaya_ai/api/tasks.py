import json
import os
from pathlib import Path

from nyaya_ai.api.database import SessionLocal, ScanRecord
from nyaya_ai.retrieval.embedder import Embedder
from nyaya_ai.retrieval.reranker import Reranker


def run_contract_scan_task_local(
    scan_id: str,
    temp_file_path: str,
    original_filename: str,
    user_id: str | None = None,
    embedder: Embedder | None = None,
    reranker: Reranker | None = None,
):
    """Background thread runner for contract scanning using FastAPI BackgroundTasks."""
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
        all_findings = []
        final_confidence = 1.0

        from nyaya_ai.contracts.scanner import scan_contract_stream

        for batch_findings, processed_count, current_status, scan_confidence in scan_contract_stream(
            file_path=path_obj,
            embedder=embedder,
            reranker=reranker,
            user_id=user_id,
        ):
            all_findings.extend(batch_findings)
            final_confidence = scan_confidence

            overall_risk = "none"
            if all_findings:
                risk_levels = [f.risk_level for f in all_findings]
                if "high" in risk_levels:
                    overall_risk = "high"
                elif "medium" in risk_levels:
                    overall_risk = "medium"
                elif "low" in risk_levels:
                    overall_risk = "low"

            # Update database with current progress (keep status as "processing")
            scan_record.status = "processing"
            scan_record.risk_level = overall_risk
            scan_record.clause_count = processed_count
            scan_record.results_json = json.dumps({
                "contract_name": original_filename,
                "total_clauses_scanned": processed_count,
                "findings": [f.model_dump() for f in all_findings],
                "scan_confidence": scan_confidence,
                "status": "processing",
                "message": f"Scan in progress... Analysed {processed_count} clauses."
            })
            db.commit()

        # Once loop exits, mark status as complete
        scan_record.status = "complete"
        scan_record.results_json = json.dumps({
            "contract_name": original_filename,
            "total_clauses_scanned": scan_record.clause_count,
            "findings": [f.model_dump() for f in all_findings],
            "scan_confidence": final_confidence,
            "status": "complete",
            "message": f"Scan complete. Identified {len(all_findings)} statutory risk findings."
        })

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
