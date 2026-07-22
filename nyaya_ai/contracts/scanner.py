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

# Clause types that must always be sent to the LLM, regardless of rerank score
HIGH_RISK_CATEGORIES = frozenset({
    "non_compete", "payment_term", "indemnity", "liability", "penalty",
})

# ---------------------------------------------------------------------------
# Statutory abbreviation → canonical token mapping
# ---------------------------------------------------------------------------
_ACT_ABBREVIATIONS: dict[str, str] = {
    "ica": "indian contract act",
    "ipc": "indian penal code",
    "crpc": "code of criminal procedure",
    "cpc": "code of civil procedure",
    "it act": "information technology act",
    "msmed": "micro small and medium enterprises development act",
    "msme": "micro small and medium enterprises development act",
    "nia": "negotiable instruments act",
    "sarfaesi": "securitisation and reconstruction of financial assets and enforcement of security interest act",
    "fema": "foreign exchange management act",
    "sebi act": "securities and exchange board of india act",
    "companies act": "companies act",
}

# Canonical tokens used for fuzzy Act matching — order matters (longer first)
_CANONICAL_ACT_TOKENS: list[str] = [
    "micro small and medium enterprises development",
    "information technology",
    "indian contract",
    "contract act",
    "indian penal code",
    "negotiable instruments",
    "foreign exchange management",
    "companies act",
    "copyright",
    "arbitration and conciliation",
    "arbitration",
    "competition",
    "consumer protection",
    "trade marks",
    "trademark",
    "patents",
    "specific relief",
    "transfer of property",
    "sale of goods",
    "partnership",
    "limited liability partnership",
    "insolvency and bankruptcy",
]


def _expand_abbreviation(text: str) -> str:
    """Expand known statutory abbreviations to canonical form."""
    lowered = text.lower().strip()
    for abbr, full in _ACT_ABBREVIATIONS.items():
        if abbr in lowered:
            return full
    return lowered


def _extract_act_tokens(act_name: str) -> set[str]:
    """Extract canonical statutory tokens from an Act name for fuzzy matching.

    Handles abbreviations (ICA, MSME, etc.), leading 'The', and year suffixes.
    Returns a set of canonical token strings that matched.
    """
    if not act_name:
        return set()

    expanded = _expand_abbreviation(act_name)
    # Strip leading "the "
    if expanded.startswith("the "):
        expanded = expanded[4:]
    # Strip trailing year
    expanded = re.sub(r"\b\d{4}\b", "", expanded).strip()
    # Remove punctuation, collapse whitespace
    expanded = re.sub(r"[^\w\s]", "", expanded)
    expanded = " ".join(expanded.split())

    matched: set[str] = set()
    for token in _CANONICAL_ACT_TOKENS:
        if token in expanded:
            matched.add(token)
    # If nothing matched, use the cleaned string itself as a token
    if not matched and expanded:
        matched.add(expanded)
    return matched


def _extract_section_digits(sec: str) -> str:
    """Normalize a section reference to just digits and sub-clause letters.

    Examples:
        'Section 27'     → '27'
        'Sec. 43A'       → '43a'
        '19(1)(g)'       → '19'
        'Section 15/16'  → '15'  (first section extracted)
        'clause 7.2'     → '7'
    """
    if not sec:
        return ""
    sec = sec.lower().strip()
    # Remove common prefixes
    sec = re.sub(r"^(?:section|sec\.?|article|art\.?|clause|cl\.?)\s*", "", sec)
    # Extract leading digits + optional sub-clause letter (e.g., 43A, 27, 15)
    m = re.match(r"(\d+[a-z]?)", sec)
    return m.group(1) if m else sec.strip()


def normalize_text(text: str) -> str:
    """Normalize text for grounding matches."""
    if not text:
        return ""
    text = text.lower().strip()
    if text.startswith("the "):
        text = text[4:].strip()
    text = re.sub(r"[^\w\s]", "", text)
    text = " ".join(text.split())
    return text


def verify_grounding(assessment: RiskAssessment, retrieved_chunks: list[dict]) -> bool:
    """Verify that the LLM risk assessment is grounded in the retrieved statutory context.

    Uses three-stage matching:
    1. Canonical Act token overlap + normalized section digit match
    2. Normalized text substring match (backward-compatible)
    3. Soft fallback: for high/medium risk with confidence > 0.75,
       check if conflicting_law_quote appears in any chunk text
    """
    if not assessment.conflicting_act or not assessment.conflicting_section:
        # Soft fallback for high/medium without act/section — quote-based
        if (
            assessment.risk_level in ("high", "medium")
            and assessment.confidence > 0.75
            and assessment.conflicting_law_quote
        ):
            quote_lower = assessment.conflicting_law_quote.lower().strip()
            if len(quote_lower) > 20:  # non-trivial quote
                for chunk in retrieved_chunks:
                    chunk_text = (chunk.get("text", "") or "").lower()
                    if quote_lower in chunk_text:
                        return True
        return False

    # --- Stage 1: Canonical token matching ---
    llm_act_tokens = _extract_act_tokens(assessment.conflicting_act)
    llm_sec = _extract_section_digits(assessment.conflicting_section)

    for chunk in retrieved_chunks:
        chunk_act_tokens = _extract_act_tokens(chunk.get("act_name", ""))
        chunk_sec = _extract_section_digits(chunk.get("section_number", ""))

        # Act matches if there is any overlap in canonical tokens
        act_matches = bool(llm_act_tokens & chunk_act_tokens)

        # Section matches if digits match
        sec_matches = (
            llm_sec and chunk_sec and (
                llm_sec == chunk_sec
                or llm_sec in chunk_sec
                or chunk_sec in llm_sec
            )
        )

        if act_matches and sec_matches:
            return True

    # --- Stage 2: Normalized text substring matching (backward-compatible) ---
    norm_act = normalize_text(assessment.conflicting_act)
    norm_act_no_year = re.sub(r"\b\d{4}\b", "", norm_act).strip()

    for chunk in retrieved_chunks:
        chunk_act = normalize_text(chunk.get("act_name", ""))
        chunk_act_no_year = re.sub(r"\b\d{4}\b", "", chunk_act).strip()
        chunk_sec = _extract_section_digits(chunk.get("section_number", ""))

        act_matches = (
            norm_act in chunk_act
            or chunk_act in norm_act
            or norm_act_no_year in chunk_act_no_year
            or chunk_act_no_year in norm_act_no_year
        )
        sec_matches = llm_sec and chunk_sec and (
            llm_sec == chunk_sec
            or llm_sec in chunk_sec
            or chunk_sec in llm_sec
        )

        if act_matches and sec_matches:
            return True

    # --- Stage 3: Soft fallback for high/medium confidence findings ---
    # Requires act token overlap plus quote presence in chunk text.
    # Section-only is insufficient because many Acts share section numbers
    # (e.g., "43A" exists in both IT Act and Companies Act).
    if (
        assessment.risk_level in ("high", "medium")
        and assessment.confidence > 0.75
        and assessment.conflicting_law_quote
    ):
        quote_lower = assessment.conflicting_law_quote.lower().strip()
        if len(quote_lower) > 20:
            for chunk in retrieved_chunks:
                chunk_act_tokens = _extract_act_tokens(chunk.get("act_name", ""))
                chunk_text = (chunk.get("text", "") or "").lower()

                # Act must match — section numbers are not unique across Acts
                if bool(llm_act_tokens & chunk_act_tokens) and quote_lower in chunk_text:
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

        # High-risk clause types always get LLM assessment, regardless of rerank score
        is_high_risk_type = best_guess_type in HIGH_RISK_CATEGORIES
        if max_score < relevance_threshold and not is_high_risk_type:
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
