from __future__ import annotations

from pathlib import Path
import re
from typing import Optional, Generator

from nyaya_ai.config import (
    CONTRACT_RELEVANCE_THRESHOLD,
    CONTRACT_RISK_TOP_K,
    RERANK_CANDIDATES,
)
from nyaya_ai.contracts.extractor import extract_contract_text
from nyaya_ai.contracts.chunker import chunk_contract
from nyaya_ai.contracts.classifier import classify_clause
from nyaya_ai.llm.cascade import cascade_risk_assessment
from nyaya_ai.schemas import ContractScanResult, RiskFinding, RiskAssessment
from nyaya_ai.store import qdrant
from nyaya_ai.retrieval.embedder import Embedder
from nyaya_ai.retrieval.reranker import Reranker


def normalize_text(text: str) -> str:
    """Normalize text for grounding matches."""
    if not text:
        return ""
    text = text.lower().strip()
    # Remove leading "the "
    if text.startswith("the "):
        text = text[4:].strip()
    # Remove punctuation
    text = re.sub(r"[^\w\s]", "", text)
    # Collapse whitespace
    text = " ".join(text.split())
    return text


def normalize_section(sec: str) -> str:
    """Normalize section number for grounding matches."""
    if not sec:
        return ""
    sec = sec.lower().strip()
    # Remove common prefixes like 'section', 'sec', 'clause', 'cl', etc.
    sec = re.sub(r"^(?:section|sec|article|art|cl|clause)\s*", "", sec)
    # Remove surrounding punctuation
    sec = re.sub(r"[^\w\s\(\)]", "", sec)
    return sec.strip()


def verify_grounding(assessment: RiskAssessment, retrieved_chunks: list[dict]) -> bool:
    """Verify that the LLM risk assessment is grounded in the retrieved context.

    Checks if the cited Act, Section, and Quote exist within the retrieved
    statutory sections.
    """
    if not assessment.conflicting_act or not assessment.conflicting_section:
        return False

    norm_act = normalize_text(assessment.conflicting_act)
    norm_sec = normalize_section(assessment.conflicting_section)
    norm_quote = normalize_text(assessment.conflicting_law_quote or "")

    # Loose Act name match by removing the year if present
    norm_act_no_year = re.sub(r"\b\d{4}\b", "", norm_act).strip()

    for chunk in retrieved_chunks:
        chunk_act = normalize_text(chunk.get("act_name", ""))
        chunk_act_no_year = re.sub(r"\b\d{4}\b", "", chunk_act).strip()
        chunk_sec = normalize_section(chunk.get("section_number", ""))
        chunk_text = normalize_text(chunk.get("text", ""))

        # Match Act
        act_matches = (norm_act == chunk_act) or (norm_act_no_year == chunk_act_no_year)
        # Match Section number
        sec_matches = (norm_sec == chunk_sec)
        # Match Quote (substring match)
        quote_matches = True
        if norm_quote:
            quote_matches = (norm_quote in chunk_text) or (chunk_text in norm_quote)

        if act_matches and sec_matches and quote_matches:
            return True

    return False


def scan_contract_stream(
    file_path: Path,
    *,
    relevance_threshold: float = CONTRACT_RELEVANCE_THRESHOLD,
    top_k: int = CONTRACT_RISK_TOP_K,
    verbose: bool = False,
    embedder: Optional[Embedder] = None,
    reranker: Optional[Reranker] = None,
    user_id: Optional[str] = None,
) -> Generator[tuple[list[RiskFinding], int, str, float], None, None]:
    """Generator version of contract scanner. 
    
    Processes clauses in small pipelining queues (batches of 3) to keep CPU overhead low 
    and yields findings in real-time.
    """
    path = Path(file_path)
    contract_name = path.name

    # 1. Extract contract text
    extraction = extract_contract_text(path)
    if extraction.status == "ocr_required":
        yield [], 0, "ocr_required", 0.0
        return
    elif extraction.status == "failure":
        raise ValueError(extraction.error_message or "Unknown extraction failure.")

    # 2. Chunk contract structurally
    clauses = chunk_contract(extraction, user_id=user_id)
    if not clauses:
        yield [], 0, "no_material_risks_found", 1.0
        return

    if embedder is None:
        embedder = Embedder()
    if reranker is None:
        reranker = Reranker()

    # Index clauses into Qdrant 'nyaya_contracts' collection (ignoring failures)
    try:
        qdrant.create_collection("nyaya_contracts")
        clause_vectors = [embedder.embed_query(c.clause_text) for c in clauses]
        qdrant.upsert_chunks(clauses, clause_vectors, collection_name="nyaya_contracts")
    except Exception:
        pass

    # ThreadPool execution function for concurrent processing
    from concurrent.futures import ThreadPoolExecutor

    def process_single_clause(clause, delay: float = 0.0):
        best_guess_type, best_guess_detail = classify_clause(clause.clause_text)

        # Single clause embedding (fast on CPU with batch size 1)
        query_hybrid = embedder.embed_query_hybrid(clause.clause_text)
        candidates = qdrant.search(
            query_vector=query_hybrid.dense,
            sparse_vector=query_hybrid.sparse,
            top_k=RERANK_CANDIDATES,
            collection_name="nyaya_corpus",
        )

        # Introduce staggered delay to avoid parallel rate-limiting on Jina API
        if delay > 0:
            import time
            time.sleep(delay)

        # Cross-encoder rerank
        retrieved_chunks = reranker.rerank(
            query=clause.clause_text,
            candidates=candidates,
            top_k=top_k,
        )

        # Precedents
        precedent_chunks = []
        try:
            from nyaya_ai.config import PRECEDENTS_COLLECTION_NAME
            precedent_candidates = qdrant.search(
                query_vector=query_hybrid.dense,
                sparse_vector=query_hybrid.sparse,
                top_k=3,
                collection_name=PRECEDENTS_COLLECTION_NAME,
            )
            precedent_chunks = precedent_candidates
        except Exception:
            pass

        max_score = max([c["rerank_score"] for c in retrieved_chunks]) if retrieved_chunks else 0.0

        if max_score < relevance_threshold:
            return None, best_guess_type, best_guess_detail, 0.0, False

        # Invoke LLM Cascade
        assessment = cascade_risk_assessment(
            clause_text=clause.clause_text,
            context_chunks=retrieved_chunks,
            best_guess_type=best_guess_type,
            precedent_chunks=precedent_chunks,
        )

        finding = None
        grounded = False
        if assessment.risk_level != "none":
            grounded = verify_grounding(assessment, retrieved_chunks)
            if grounded:
                finding = RiskFinding(
                    clause_number=clause.clause_number,
                    clause_text=clause.clause_text,
                    page=clause.page,
                    clause_type=assessment.clause_type,
                    risk_level=assessment.risk_level,
                    conflicting_act=assessment.conflicting_act,
                    conflicting_section=assessment.conflicting_section,
                    conflicting_law_quote=assessment.conflicting_law_quote,
                    explanation=assessment.explanation,
                    recommended_action=assessment.recommended_action,
                    confidence=assessment.confidence,
                    relevant_precedents=assessment.relevant_precedents or [],
                )

        return finding, assessment.clause_type, assessment.clause_type_detail, assessment.confidence, True

    # Pipelined small-batch queue (batches of 2)
    findings = []
    scanned_count = 0
    llm_scanned_count = 0
    confidence_sum = 0.0

    batch_size = 2
    for i in range(0, len(clauses), batch_size):
        batch = clauses[i : i + batch_size]
        batch_findings = []

        with ThreadPoolExecutor(max_workers=len(batch)) as executor:
            futures = [executor.submit(process_single_clause, c, float(idx * 1.0)) for idx, c in enumerate(batch)]
            for idx, future in enumerate(futures):
                clause = batch[idx]
                try:
                    finding, c_type, c_detail, confidence, passed_gate = future.result()
                    clause.clause_type = c_type
                    clause.clause_type_detail = c_detail

                    if passed_gate:
                        scanned_count += 1
                        confidence_sum += confidence
                        llm_scanned_count += 1
                        if finding:
                            batch_findings.append(finding)
                            findings.append(finding)
                except Exception as thread_err:
                    print(f"[Error] Thread execution failure on clause #{clause.clause_number}: {thread_err}")

        # Determine intermediate status
        current_status = "processing"
        if findings:
            current_status = "risks_found"
        elif i + batch_size >= len(clauses):
            current_status = "no_material_risks_found" if scanned_count > 0 else "insufficient_evidence"

        scan_confidence = confidence_sum / llm_scanned_count if llm_scanned_count > 0 else 1.0
        yield batch_findings, min(i + batch_size, len(clauses)), current_status, scan_confidence


def scan_contract(
    file_path: Path,
    *,
    relevance_threshold: float = CONTRACT_RELEVANCE_THRESHOLD,
    top_k: int = CONTRACT_RISK_TOP_K,
    verbose: bool = False,
    embedder: Optional[Embedder] = None,
    reranker: Optional[Reranker] = None,
    user_id: Optional[str] = None,
) -> ContractScanResult:
    """Extract, chunk, retrieve, gate, and assess contract risks.

    Maintains backward compatibility by consuming the streaming generator.
    """
    path = Path(file_path)
    contract_name = path.name
    all_findings = []
    final_count = 0
    final_status = "processing"
    final_confidence = 1.0

    # Consume streaming generator to the end
    for batch_findings, processed_count, status, confidence in scan_contract_stream(
        file_path,
        relevance_threshold=relevance_threshold,
        top_k=top_k,
        verbose=verbose,
        embedder=embedder,
        reranker=reranker,
        user_id=user_id,
    ):
        all_findings.extend(batch_findings)
        final_count = processed_count
        final_status = status
        final_confidence = confidence

    # Final summary message matching expected schema outputs
    if final_status == "risks_found":
        message = f"Scan complete. Identified {len(all_findings)} statutory risk findings."
    elif final_status == "no_material_risks_found":
        message = "Scan complete. No material statutory risks identified in the contract."
    else:
        message = "Scan complete. No material risks identified, but retrieval found no relevant Indian laws to evaluate against."

    return ContractScanResult(
        contract_name=contract_name,
        total_clauses_scanned=final_count,
        findings=all_findings,
        scan_confidence=final_confidence,
        status=final_status,
        message=message,
    )
