from __future__ import annotations

from pathlib import Path
import re
from typing import Optional

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

    Saves extracted clauses to Qdrant collection 'nyaya_contracts'.
    Validates findings against retrieved context (grounding).

    Args:
        file_path: Path to the contract file (PDF or DOCX).
        relevance_threshold: Permissive cosine similarity gate.
        top_k: Number of retrieved statutory sections from nyaya_corpus.
        verbose: Print detailed step-by-step evaluation logs to console.
        embedder: Optional preloaded Embedder singleton.
        reranker: Optional preloaded Reranker singleton.
        user_id: Optional owner ID of the contract.

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
    clauses = chunk_contract(extraction, user_id=user_id)

    if not clauses:
        return ContractScanResult(
            contract_name=contract_name,
            total_clauses_scanned=0,
            findings=[],
            scan_confidence=1.0,
            status="no_material_risks_found",
            message="Contract contains no readable clauses to scan.",
        )

    if embedder is None:
        embedder = Embedder()
    if reranker is None:
        reranker = Reranker()

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

    verbose_logs = []
    if verbose:
        from rich.console import Console
        from rich.table import Table
        from rich.panel import Panel
        c_logger = Console()
        
        def log_verbose(msg: str):
            c_logger.print(msg)
            # Strip simple rich tags for the raw log file
            import re
            plain = re.sub(r"\[/?(?:bold|dim|italic|red|green|blue|cyan|magenta|yellow|white|/)[^\]]*?\]", "", msg)
            verbose_logs.append(plain)
            
        log_verbose(
            f"[bold cyan]Starting Verbose Diagnostic Scan[/]\n"
            f"Contract: [cyan]{contract_name}[/]\n"
            f"Clauses Found: [cyan]{len(clauses)}[/]"
        )
    else:
        def log_verbose(msg: str):
            pass

    # Pre-embed all clauses in one batch pass (huge CPU speedup)
    clause_texts = [c.clause_text for c in clauses]
    hybrid_embeddings = embedder.embed_documents_hybrid(clause_texts, batch_size=32)

    # 4. Assess risks for each clause in parallel
    findings: list[RiskFinding] = []
    scanned_count = 0
    llm_scanned_count = 0
    confidence_sum = 0.0

    verbose_logs = []
    if verbose:
        from rich.console import Console
        from rich.table import Table
        from rich.panel import Panel
        c_logger = Console()
        
        def log_verbose(msg: str):
            c_logger.print(msg)
            import re
            plain = re.sub(r"\[/?(?:bold|dim|italic|red|green|blue|cyan|magenta|yellow|white|/)[^\]]*?\]", "", msg)
            verbose_logs.append(plain)
            
        log_verbose(
            f"[bold cyan]Starting Verbose Diagnostic Scan[/]\n"
            f"Contract: [cyan]{contract_name}[/]\n"
            f"Clauses Found: [cyan]{len(clauses)}[/]"
        )
    else:
        def log_verbose(msg: str):
            pass

    # ThreadPool execution function for concurrent processing
    from concurrent.futures import ThreadPoolExecutor
    
    def process_single_clause(clause_idx: int, clause):
        best_guess_type, best_guess_detail = classify_clause(clause.clause_text)

        # Retrieve vectors from the pre-embedded batch output
        dense_vec = hybrid_embeddings.dense[clause_idx]
        sparse_vec = hybrid_embeddings.sparse[clause_idx]

        # Retrieve applicable law chunks via hybrid search (concurrent Qdrant call)
        candidates = qdrant.search(
            query_vector=dense_vec,
            sparse_vector=sparse_vec,
            top_k=RERANK_CANDIDATES,
            collection_name="nyaya_corpus",
        )

        # Cross-encoder rerank → top_k best matches
        retrieved_chunks = reranker.rerank(
            query=clause.clause_text,
            candidates=candidates,
            top_k=top_k,
        )

        # Retrieve matching case law precedents from nyaya_precedents (concurrent Qdrant call)
        precedent_chunks = []
        try:
            from nyaya_ai.config import PRECEDENTS_COLLECTION_NAME
            precedent_candidates = qdrant.search(
                query_vector=dense_vec,
                sparse_vector=sparse_vec,
                top_k=3,
                collection_name=PRECEDENTS_COLLECTION_NAME,
            )
            precedent_chunks = precedent_candidates
        except Exception:
            pass

        # Relevance pre-filter gate (using reranker score)
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

    # Run execution loop concurrently (supports up to 8 parallel requests to Groq/Gemini/Qdrant)
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(process_single_clause, i, c) for i, c in enumerate(clauses)]
        for idx, future in enumerate(futures):
            clause = clauses[idx]
            try:
                finding, c_type, c_detail, confidence, passed_gate = future.result()
                clause.clause_type = c_type
                clause.clause_type_detail = c_detail

                if passed_gate:
                    scanned_count += 1
                    confidence_sum += confidence
                    llm_scanned_count += 1
                    if finding:
                        findings.append(finding)
            except Exception as thread_err:
                print(f"[Error] Thread execution failure on clause #{clause.clause_number}: {thread_err}")

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

    if verbose:
        log_verbose(f"\n[bold green]✓ Diagnostic Scan Complete![/] Status: {status.upper()} | Findings: {len(findings)}\n")
        # Save plain text log to scan_debug.txt
        try:
            with open("scan_debug.txt", "w", encoding="utf-8") as f:
                f.write("\n".join(verbose_logs))
            c_logger.print("[dim cyan]Detailed log saved to scan_debug.txt[/]")
        except Exception as e:
            c_logger.print(f"[red]Failed to save log to scan_debug.txt: {e}[/]")

    return ContractScanResult(
        contract_name=contract_name,
        total_clauses_scanned=len(clauses),
        findings=findings,
        scan_confidence=scan_confidence,
        status=status,
        message=message,
    )
