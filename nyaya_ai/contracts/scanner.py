from __future__ import annotations

from pathlib import Path
import re
from nyaya_ai.config import CONTRACT_RELEVANCE_THRESHOLD, CONTRACT_RISK_TOP_K
from nyaya_ai.contracts.extractor import extract_contract_text
from nyaya_ai.contracts.chunker import chunk_contract
from nyaya_ai.contracts.classifier import classify_clause
from nyaya_ai.llm.cascade import cascade_risk_assessment
from nyaya_ai.schemas import ContractScanResult, RiskFinding, RiskAssessment
from nyaya_ai.store import qdrant
from nyaya_ai.retrieval.embedder import Embedder


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


def scan_contract(
    file_path: Path,
    *,
    relevance_threshold: float = CONTRACT_RELEVANCE_THRESHOLD,
    top_k: int = CONTRACT_RISK_TOP_K,
) -> ContractScanResult:
    """Extract, chunk, retrieve, gate, and assess contract risks.

    Saves extracted clauses to Qdrant collection 'nyaya_contracts'.
    Validates findings against retrieved context (grounding).

    Args:
        file_path: Path to the contract file (PDF or DOCX).
        relevance_threshold: Permissive cosine similarity gate.
        top_k: Number of retrieved statute sections from nyaya_corpus.

    Returns:
        ContractScanResult summary and detailed risk findings.
    """
    path = Path(file_path)
    contract_name = path.name

    # 1. Extract contract text
    extraction = extract_contract_text(path)
    if extraction.status == "ocr_required":
        return ContractScanResult(
            contract_name=contract_name,
            total_clauses_scanned=0,
            findings=[],
            scan_confidence=0.0,
            status="ocr_required",
            message="Contract text extraction failed. Document appears to be a scanned image and requires OCR.",
        )
    elif extraction.status == "failure":
        raise ValueError(extraction.error_message or "Unknown extraction failure.")

    # 2. Chunk contract structurally
    clauses = chunk_contract(extraction)
    if not clauses:
        return ContractScanResult(
            contract_name=contract_name,
            total_clauses_scanned=0,
            findings=[],
            scan_confidence=1.0,
            status="no_material_risks_found",
            message="Contract contains no readable clauses to scan.",
        )

    embedder = Embedder()

    # 3. Index clauses into Qdrant 'nyaya_contracts' collection (ignoring failures)
    try:
        qdrant.create_collection("nyaya_contracts")
        clause_vectors = [embedder.embed_query(c.clause_text) for c in clauses]
        qdrant.upsert_chunks(clauses, clause_vectors, collection_name="nyaya_contracts")
    except Exception:
        # Proceed even if local contract indexing fails, as it shouldn't block the scan
        pass

    # 4. Assess risks for each clause
    findings: list[RiskFinding] = []
    scanned_count = 0
    llm_scanned_count = 0
    confidence_sum = 0.0

    for clause in clauses:
        best_guess_type, best_guess_detail = classify_clause(clause.clause_text)

        # Retrieve applicable law chunks
        query_vector = embedder.embed_query(clause.clause_text)
        retrieved_chunks = qdrant.search(
            query_vector, top_k=top_k, collection_name="nyaya_corpus"
        )

        max_score = max([c["score"] for c in retrieved_chunks]) if retrieved_chunks else 0.0

        # Relevance pre-filter gate
        if max_score < relevance_threshold:
            # Skip LLM call, record best-guess details
            clause.clause_type = best_guess_type
            clause.clause_type_detail = best_guess_detail
            continue

        # Invoke LLM Cascade
        scanned_count += 1
        assessment = cascade_risk_assessment(
            clause_text=clause.clause_text,
            context_chunks=retrieved_chunks,
            best_guess_type=best_guess_type,
        )

        # Update clause with LLM classification
        clause.clause_type = assessment.clause_type
        clause.clause_type_detail = assessment.clause_type_detail

        # Grounding verification step
        if assessment.risk_level != "none":
            if verify_grounding(assessment, retrieved_chunks):
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
                )
                findings.append(finding)
                confidence_sum += assessment.confidence
                llm_scanned_count += 1
        else:
            confidence_sum += assessment.confidence
            llm_scanned_count += 1

    # 5. Assemble scan summary status
    scan_confidence = confidence_sum / llm_scanned_count if llm_scanned_count > 0 else 1.0

    if findings:
        status = "risks_found"
        message = f"Scan complete. Identified {len(findings)} statutory risk findings."
    elif scanned_count > 0:
        status = "no_material_risks_found"
        message = "Scan complete. No material statutory risks identified in the contract."
    else:
        status = "insufficient_evidence"
        message = "Scan complete. No material risks identified, but retrieval found no relevant Indian laws to evaluate against."

    return ContractScanResult(
        contract_name=contract_name,
        total_clauses_scanned=len(clauses),
        findings=findings,
        scan_confidence=scan_confidence,
        status=status,
        message=message,
    )
