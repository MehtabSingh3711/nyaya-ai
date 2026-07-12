# AI Session Log — 2026-07-12 — Mode 1 Generic Contract Risk Scanner
**Agent:** ChatGPT Codex
**Phase:** Week 3 — Core
**Session opened:** 2026-07-12 (Asia/Kolkata)

## Session Goal
Build the Mode 1 generic contract risk scanner: ingest an uploaded Indian contract, extract structural clauses, retrieve applicable provisions from the entire `nyaya_corpus`, and return only grounded risk findings without hardcoded per-Act scan paths.

## Decisions Log

### Decision: Clause type categorization
**Options presented:** A — fixed taxonomy; B — free-form labels; C — fixed taxonomy plus detail
**Student chose:** C — fixed taxonomy plus detail
**Student's reason (if given):** not stated
**Agent recommendation was:** C — fixed taxonomy plus detail
**Student followed agent recommendation:** Yes
**Logged at:** 2026-07-12 (Asia/Kolkata)

### Decision: LLM scan relevance pre-filter
**Options presented:** A — scan every clause; B — strict similarity gate; C — permissive relevance gate
**Student chose:** C — permissive relevance gate
**Student's reason (if given):** not stated
**Agent recommendation was:** C — permissive relevance gate
**Student followed agent recommendation:** Yes
**Logged at:** 2026-07-12 (Asia/Kolkata)

### Decision: No-risk scan result
**Options presented:** A — empty findings only; B — clean status; C — evidence-aware status
**Student chose:** C — evidence-aware status
**Student's reason (if given):** not stated
**Agent recommendation was:** C — evidence-aware status
**Student followed agent recommendation:** Yes
**Logged at:** 2026-07-12 (Asia/Kolkata)

### Decision: Statutory amendment-currency scope
**Options presented:** Continue with the current `mratanusarkar/Indian-Laws` corpus; replace critical Acts with India Code before Mode 1
**Student chose:** Continue Mode 1 using the current corpus; defer upgrading ICA, MSME Act, IT Act, IPC, and CPC to `indiacode.nic.in` until Mode 1 is functional.
**Student's reason (if given):** Independent verification indicates India Code reflects amendments (including IT Act §66A as omitted and §43A as amended), while the current source may not track amendments equivalently; this is not to block the sprint.
**Agent recommendation was:** Not stated before the student's independent decision.
**Student followed agent recommendation:** N/A
**Logged at:** 2026-07-12 (Asia/Kolkata)

**Documented limitation:** Findings are grounded only in the current corpus snapshot and must not be represented as a guarantee of amendment-current law. A replacement of critical statutory sources with India Code remains planned after Mode 1 is functional.

### Decision: Corpus amendment-currency ADR number
**Options presented:** A — corpus currency becomes ADR-010 and deployment becomes ADR-011; B — deployment remains ADR-010 and corpus currency becomes ADR-011; C — assign the corpus ADR number later
**Student chose:** B — deployment remains ADR-010 and corpus amendment currency becomes ADR-011
**Student's reason (if given):** Preserve the original ADR-010 deployment reservation.
**Agent recommendation was:** A — corpus currency as ADR-010 and deployment as ADR-011
**Student followed agent recommendation:** No
**Logged at:** 2026-07-12 (Asia/Kolkata)

**Planned ADR-011:** Upgrade critical Act sources (ICA, MSME Act, IT Act, IPC, and CPC) from `mratanusarkar/Indian-Laws` to `indiacode.nic.in` for amendment currency. **Status:** planned, not yet built; scheduled after Mode 1 is functional.

### Decision: Initial contract parser
**Options presented:** A — PyMuPDF + Unstructured + PaddleOCR; B — native-text MVP; C — native-text parser behind an interface
**Student chose:** C — PyMuPDF for PDFs and `python-docx` for DOCX behind a `ContractTextExtractor` boundary; scanned PDFs return an explicit OCR-required outcome.
**Student's reason (if given):** not stated
**Agent recommendation was:** C — native-text parser behind an interface
**Student followed agent recommendation:** Yes
**Logged at:** 2026-07-12 (Asia/Kolkata)

### Decision: Relevance gate threshold configuration
**Options presented:** A — fixed score hardcoded; B — tunable config with default threshold and logged skipped clauses; C — relative ranking
**Student chose:** B — tunable config with default threshold and logged skipped clauses
**Student's reason (if given):** not stated
**Agent recommendation was:** B — tunable config with default threshold and logged skipped clauses
**Student followed agent recommendation:** Yes
**Logged at:** 2026-07-12 (Asia/Kolkata)

### Decision: Clause type assignment
**Options presented:** A — separate LLM extraction call; B — deterministic structural extraction; C — single combined risk call
**Student chose:** C — extract structural fields locally, then have the risk LLM confirm or improve `clause_type` only for clauses that pass the relevance gate
**Student's reason (if given):** not stated
**Agent recommendation was:** C — single combined risk call
**Student followed agent recommendation:** Yes
**Logged at:** 2026-07-12 (Asia/Kolkata)

## Code / Output Produced

- Draft feature spec: `docs/specs/mode-1-generic-contract-risk-scanner.md`

## What the Student Built / Decided

_Pending._

## Open Questions for Next Session

_Pending._

## Next Session Goal

_Pending._
