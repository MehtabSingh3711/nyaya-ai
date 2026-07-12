# Spec: Mode 1 Generic Contract Risk Scanner

## Objective

Build Mode 1 Contract Intelligence for Nyaya AI: a CLI-first scanner that ingests an uploaded Indian contract, extracts clause-level structure, retrieves relevant statutory sections from the entire `nyaya_corpus`, and returns grounded risk findings only when the clause appears to conflict with, be voided by, or violate retrieved Indian statutory law.

The scanner must be generic. It must not contain special code paths for Indian Contract Act Section 27, the MSME Act, or any other individual law. Those risks should emerge from full-corpus retrieval plus the risk-assessment prompt.

Primary user outcome: given a PDF or DOCX contract, the user sees which clauses need attention, which Act and section create the issue, the supporting statutory quote, risk level, explanation, recommended action, and confidence.

## Confirmed Decisions

- Clause typing: use a fixed taxonomy plus detail.
- Relevance pre-filter: use a permissive relevance gate before LLM calls.
- Relevance gate configuration: expose the threshold as config, log skipped clauses and scores, and calibrate with validation tests.
- No-risk result: return an evidence-aware status rather than only an empty list.
- Contract parser: support native-text PDF via PyMuPDF and DOCX via `python-docx` behind a `ContractTextExtractor`; scanned PDFs return an explicit OCR-required outcome.
- Clause type assignment: extract structural fields locally; for clauses passing the relevance gate, ask the risk LLM to confirm or improve `clause_type` inside the single risk assessment call.
- Corpus currency: use the current `mratanusarkar/Indian-Laws` corpus for this sprint; document amendment-currency limitations under planned ADR-011.

## Tech Stack

- Python 3.11+
- Pydantic v2 for all structured scanner inputs and outputs
- PyMuPDF for native-text PDF extraction
- `python-docx` for DOCX extraction
- BGE-M3 embeddings through existing `nyaya_ai.retrieval.embedder.Embedder`
- Qdrant local file-based vector store
- Existing Groq -> Gemini -> OpenRouter LLM cascade, extended to validate a risk-assessment schema
- Rich for CLI output
- Pytest for unit and integration-style tests

## Commands

- Install/update dependencies: `python -m pip install -r requirements.txt`
- Run the full test suite: `python -m pytest`
- Run Mode 2 chat, unchanged: `python query.py`
- Run Mode 1 scan after implementation: `python scan_contract.py path\to\contract.pdf`
- Run Mode 1 scan with JSON output after implementation: `python scan_contract.py path\to\contract.docx --json`

## Project Structure

- `nyaya_ai/schemas.py`
  - Add `ClauseExtraction`, `RiskAssessment`, `RiskFinding`, and `ContractScanResult`.
  - Keep existing `Citation`, `CitedAnswer`, and `CorpusChunk` backward compatible.

- `nyaya_ai/contracts/`
  - `extractor.py`: PDF/DOCX text extraction boundary.
  - `chunker.py`: clause-boundary aware contract chunking.
  - `classifier.py`: local best-guess clause type and detail.
  - `scanner.py`: orchestration for embed -> retrieve -> gate -> LLM risk assessment -> final result.

- `nyaya_ai/llm/`
  - Extend the cascade with a schema-generic structured call or add a narrowly scoped `cascade_risk_assessment` wrapper using the same tier functions.
  - Add a risk-assessment prompt that permits conclusions only from retrieved law sections.

- `nyaya_ai/store/qdrant.py`
  - Add collection-name aware helpers for `nyaya_contracts` while preserving current `nyaya_corpus` behavior for Mode 2.

- `scan_contract.py`
  - CLI entry point for Mode 1.

- `tests/`
  - Add contract extraction, chunking, schema, scanner, and CLI-adjacent tests.

- `docs/`
  - Record generic scanner decision as an ADR before finalizing the build.
  - Keep ADR-011 reserved for corpus amendment-currency upgrade with status planned, not yet built.

## Data Contracts

```python
class ClauseExtraction(BaseModel):
    contract_id: str
    contract_name: str
    clause_number: str
    clause_text: str
    page: int
    clause_type: Literal[
        "payment_term",
        "termination",
        "liability",
        "IP",
        "non_compete",
        "indemnity",
        "arbitration",
        "other",
    ]
    clause_type_detail: str | None = None


class RiskFinding(BaseModel):
    clause_number: str
    clause_text: str
    page: int
    clause_type: str
    risk_level: Literal["high", "medium", "low"]
    conflicting_act: str
    conflicting_section: str
    conflicting_law_quote: str
    explanation: str
    recommended_action: str
    confidence: float


class ContractScanResult(BaseModel):
    contract_name: str
    total_clauses_scanned: int
    findings: list[RiskFinding]
    scan_confidence: float
    status: Literal[
        "risks_found",
        "no_material_risks_found",
        "insufficient_evidence",
        "ocr_required",
    ]
    message: str
```

Internal LLM output may use `RiskAssessment` with `risk_level: Literal["high", "medium", "low", "none"]`; only non-`none` assessments become `RiskFinding`.

## Code Style

Mode 1 should match the existing repository style: small modules, plain functions, typed Pydantic models at boundaries, and explicit failure states.

```python
def scan_contract(path: Path, *, top_k: int = CONTRACT_RISK_TOP_K) -> ContractScanResult:
    extraction = extract_contract_text(path)
    if extraction.status == "ocr_required":
        return ContractScanResult.ocr_required(contract_name=path.name)

    clauses = chunk_contract(extraction)
    findings = []
    for clause in clauses:
        assessment = assess_clause_risk(clause, top_k=top_k)
        if assessment.risk_level != "none":
            findings.append(assessment.to_finding(clause))
    return ContractScanResult.from_findings(path.name, clauses, findings)
```

## Testing Strategy

Use deterministic tests for core behavior and optional integration checks for real corpus behavior.

- Schema tests:
  - `RiskFinding` accepts only `high`, `medium`, `low`.
  - Internal `RiskAssessment` accepts `none`.
  - `ContractScanResult` supports empty findings with `no_material_risks_found`.

- Extraction and chunking tests:
  - Native PDF text extracts page numbers.
  - DOCX text extracts paragraphs and headings.
  - Scanned/empty PDF returns `ocr_required`.
  - Numbered clauses split without merging unrelated clauses.

- Scanner tests with fake embedder/retriever/LLM:
  - Employment non-compete can produce an ICA Section 27 finding through retrieved law evidence.
  - MSME 90-day payment term can produce an MSME Act finding through retrieved law evidence.
  - Standard confidentiality clause with no issue produces no finding.
  - Data localization clause can produce an IT Act-style finding from retrieved IT Act evidence.
  - No test should depend on hardcoded production engines for ICA, MSME, or IT Act.

- Relevance gate tests:
  - Clause below configured threshold skips LLM and records skipped score.
  - Clause at or above threshold calls LLM exactly once.

- Existing Mode 2 tests:
  - Must continue passing unchanged.

## Boundaries

- Always:
  - Retrieve from the full `nyaya_corpus` without filtering to a hardcoded Act list.
  - Require the risk LLM to cite only retrieved sections.
  - Drop or refuse any LLM finding whose Act/section/quote cannot be matched to retrieved context.
  - Keep Mode 2 chat behavior backward compatible.
  - Log skipped clauses and top retrieval scores for threshold calibration.

- Ask first:
  - Adding OCR dependencies or scanned PDF OCR.
  - Adding FastAPI/frontend endpoints.
  - Replacing or reindexing statutory corpus sources.
  - Changing the LLM provider cascade order.
  - Introducing hardcoded legal rule engines.

- Never:
  - Special-case ICA Section 27, MSME Act, IT Act, or any specific statute in scanner logic.
  - Present `no_material_risks_found` as legal safety or legal advice.
  - Commit API keys, uploaded contracts, or private contract text fixtures.
  - Hide low-evidence scan failures as clean results.

## Success Criteria

- `python scan_contract.py <contract.pdf>` returns a valid `ContractScanResult`.
- Every clause is extracted structurally and indexed into `nyaya_contracts` with `contract_id`.
- Every eligible clause retrieves top-5 sections from the full `nyaya_corpus`.
- Clauses below the configured permissive gate are skipped with logged evidence.
- LLM calls return validated structured risk assessments.
- `RiskFinding` is emitted only when `risk_level` is `high`, `medium`, or `low`.
- Empty findings produce `status="no_material_risks_found"` or `status="insufficient_evidence"` depending on evidence quality.
- Validation cases pass:
  - Employment non-compete flags ICA Section 27 through retrieval evidence.
  - MSME vendor 90-day payment term flags MSME Act through retrieval evidence.
  - Standard confidentiality clause does not produce a false positive.
  - Data localization clause can surface a relevant IT Act provision through corpus-wide retrieval.
- Existing tests still pass with `python -m pytest`.

## Open Questions

- Exact default relevance threshold will be calibrated during implementation against the validation cases and stored in config.
- Real-corpus validation depends on the local `nyaya_corpus` snapshot being present and API keys being available; deterministic tests will mock these dependencies.
