# ADR-008 — Evaluation Framework

**Date:** 2026-06-26
**Status:** Accepted
**Author:** Mehtab Singh
**Decider:** Mehtab Singh
**Depends on:** ADR-004 (LLM cascade), ADR-005 (extraction framework), ADR-006 (backend — Langfuse tracing)

---

## Context

Nyaya AI has four published evaluation targets:
1. Citation precision > 90%
2. Hallucination rate < 5%
3. Extraction F1 > 0.88
4. Cost per contract < ₹0.50 (superseded by ADR-004: target is ₹0)

These are product promises, not aspirational numbers. The eval framework must measure each one with enough precision to defend the numbers in a technical interview or a mentor review. "RAGAS says it's good" is not a defensible answer. "Citation precision is 91.3% on the 100-question test set, broken down by difficulty: 96% on simple extraction, 94% on risk classification, 84% on complex legal reasoning" is.

---

## Decision Question (as posed)

> **How do you measure whether the system is actually working?**
>
> **Option A — RAGAS only**
> Run RAGAS on a test set and report faithfulness, answer relevance, context precision, context recall.
> | Why choose it | Tradeoff |
> |---|---|
> | Industry-standard; covers retrieval + generation; well-documented | Does not measure citation precision to clause level; hallucination detection is coarse; no Indian-law-specific metrics |
>
> **Option B — Custom eval harness only**
> Hand-labelled 100-question test set with custom metrics: citation match, hallucination detector, extraction F1.
> | Why choose it | Tradeoff |
> |---|---|
> | Measures exactly what the product requires | 2–3 days of labelling; no standard vocabulary for interviewers |
>
> **Option C — RAGAS + custom citation metric**
> RAGAS for faithfulness and relevance. Custom citation-precision metric checks whether cited clause and page match ground truth.
> | Why choose it | Tradeoff |
> |---|---|
> | Standard framework + domain-specific precision metric; tells the complete story | Two eval systems; RAGAS and custom metrics may disagree on edge cases |
>
> **Agent recommendation:** Option C

---

## Decision

**RAGAS + custom citation metric, with a hand-labelled 100-question test set, difficulty-tagged.**

---

## Test Set Design

### Minimum: 100 Q&A pairs, hand-labelled in Week 3

**Coverage requirements:**
- All six contract types represented: NDA, MSA, Employment, MSME Vendor, SHA, Freelancer
- Both modes covered: Mode 1 (scan outputs) and Mode 2 (chat Q&A)
- All Indian legal domains in scope: ICA §27 cases, MSME Act cases, general clause extraction

**Each test case contains:**

```python
class TestCase(BaseModel):
    id: str                              # e.g. "tc_001"
    mode: Literal["scan", "chat"]
    contract_type: str                   # e.g. "employment"
    question: str                        # the input question or "run scan on this contract"
    ground_truth_answer: str             # the correct answer in plain language
    ground_truth_citation: Citation      # exact clause number + page
    ground_truth_risk_label: Optional[Literal["high", "medium", "low", "none"]]
    difficulty: Literal[
        "simple_extraction",             # e.g. "What is the governing law?"
        "risk_classification",           # e.g. "Is there a non-compete clause?"
        "complex_legal_reasoning"        # e.g. "Explain why this non-compete may be void"
    ]
    notes: Optional[str]                 # edge case notes, ambiguity flags
```

**Difficulty distribution (target):**
- Simple extraction: ~40 cases
- Risk classification: ~35 cases
- Complex legal reasoning: ~25 cases

**Why difficulty tagging:**
A system that scores 92% overall but scores 65% on complex legal reasoning is a different product than one that scores evenly. The breakdown by difficulty is the number that tells you whether the cascade is working correctly — complex queries should be reaching Tier 2/3 and producing better outputs there.

---

## Four Metrics — Implementation

### Metric 1: Citation Precision (Custom)

**Definition:** For each system output that includes a citation, does the cited clause number and page exactly match the ground-truth citation?

```python
def citation_precision(predictions: List[SystemOutput], ground_truths: List[TestCase]) -> float:
    """
    For each prediction with a citation:
    - Exact match: clause_number AND page both match → score 1.0
    - Clause match only: clause_number matches, page ±1 → score 0.5
    - No match → score 0.0
    Returns: mean score across all predictions that have citations
    """
    scores = []
    for pred, gt in zip(predictions, ground_truths):
        if pred.citation is None:
            # cite-or-refuse fired — not counted in citation precision
            # counted separately as refuse_rate
            continue
        clause_match = pred.citation.clause_number == gt.ground_truth_citation.clause_number
        page_match = abs(pred.citation.page - gt.ground_truth_citation.page) <= 1
        if clause_match and page_match:
            scores.append(1.0)
        elif clause_match:
            scores.append(0.5)
        else:
            scores.append(0.0)
    return sum(scores) / len(scores) if scores else 0.0
```

**Target:** > 90% (weighted: exact matches must dominate the 0.5-score cases)

### Metric 2: Hallucination Rate (RAGAS Faithfulness)

**Definition:** What fraction of claims in the system's answer are not supported by the retrieved context?

RAGAS `faithfulness` score measures this. A faithfulness score below 0.80 on a test case is treated as a hallucination event.

```
hallucination_rate = count(cases where faithfulness < 0.80) / total_cases
```

**Target:** < 5% (i.e. ≤ 5 cases out of 100 below faithfulness threshold)

**Why RAGAS faithfulness rather than a custom detector:**
RAGAS decomposes the answer into claims and checks each claim against the retrieved context using an LLM-as-judge. This is more reliable than regex-based hallucination detection. The threshold (0.80) will be calibrated against the first eval run and adjusted if needed.

### Metric 3: Extraction F1 (Field-Level)

**Definition:** For Mode 1 structured extraction (`ClauseExtraction` schema), for each field in the Pydantic model, what fraction of predicted values match ground-truth values?

```python
def extraction_f1(predictions: List[ClauseExtraction], ground_truths: List[ClauseExtraction]) -> Dict[str, float]:
    """
    Per-field F1 across all test cases.
    Boolean fields: exact match.
    String fields: exact match (normalised — lowercased, stripped).
    Integer fields: exact match.
    Optional fields: None/None = correct, None/value = false negative, value/None = false positive.
    Returns: dict of {field_name: f1_score}
    """
    ...
```

**Target:** Mean field-level F1 > 0.88. Fields reported individually — a low F1 on `payment_term_days` is a different problem than a low F1 on `has_non_compete`.

### Metric 4: Cost Per Contract

**Definition:** Total token count (input + output) consumed per contract ingestion + scan run, mapped to cost.

**Implementation:** Langfuse logs every LLM call with model, input tokens, output tokens. A per-ingestion-run cost is computed by summing all Langfuse spans for that `job_id`.

**Target (ADR-004):** ₹0 — all inference is local (Ollama). Cost tracking via Langfuse remains in place to monitor token volume and latency, even if the monetary cost is zero.

---

## Eval Dashboard — Frontend Requirement

All four metrics are displayed on a live eval dashboard in the frontend (Mode 1 panel, collapsible "Eval" section). This is not a README table — it is a rendered component that updates when the eval harness is re-run.

```
┌─────────────────────────────────────────────────────┐
│  Eval Results — Last run: 2026-07-10                │
├──────────────────────┬──────────────────────────────┤
│ Citation Precision   │ 91.3%  ████████████░░ ✓      │
│ Hallucination Rate   │  3.1%  ████░░░░░░░░░░ ✓      │
│ Extraction F1        │  0.89  ████████████░░ ✓      │
│ Cost per Contract    │   ₹0   ██████████████ ✓      │
├──────────────────────┴──────────────────────────────┤
│ By difficulty:                                      │
│  Simple extraction      96.2%                      │
│  Risk classification    93.8%                      │
│  Complex legal reason.  84.1%                      │
└─────────────────────────────────────────────────────┘
```

---

## Labelling Schedule

| Week | Eval activity |
|------|---------------|
| Week 1 | 10 pilot test cases (corpus RAG only) — smoke test the pipeline |
| Week 2 | 20 additional cases as Mode 1 engines ship |
| Week 3 | Full 100-case labelling sprint (2–3 days) — against real system outputs |
| Week 4 | Eval harness runs on full test set; numbers appear in dashboard |
| Week 5 | Final eval run; numbers locked into README |

**Why Week 3 for full labelling (not earlier):**
You need real system outputs to label against. Labelling against hypothetical outputs produces a test set that doesn't reflect the actual system's failure modes. The 10 pilot cases in Week 1 and 20 in Week 2 are sufficient to catch gross failures early without the full labelling investment.

---

## Why Custom Citation Metric Is Non-Negotiable

> "RAGAS alone would not catch a system that gives correct answers with wrong clause citations, which in a legal context is a failure mode, not a minor inaccuracy."

This is the defining argument for this decision. Consider the failure case:

- Question: "Does this contract contain an enforceable non-compete?"
- Ground truth: "No — Clause 12.3 is void under ICA §27. See Clause 12.3, page 4."
- System output: "No — this non-compete is void under ICA §27." → Citation: Clause 8.1, page 2.

RAGAS faithfulness: high (the answer is grounded in retrieved context).
RAGAS answer relevance: high (correct answer to the question).
Citation precision: 0.0 (wrong clause, wrong page).

A lawyer receiving this output who then goes to Clause 8.1, page 2 finds something else. The product has failed. RAGAS did not catch it. The custom citation metric did.

This is why the custom metric is the number that makes Nyaya AI defensible as a legal product specifically.

---

## Consequences

**Positive:**
- Four metrics cover four distinct failure modes: wrong citations, hallucinated claims, incorrect field extraction, cost overrun
- Difficulty breakdown exposes cascade performance issues that overall scores hide
- Live eval dashboard in frontend makes the numbers visible to users and mentors — not buried in a README
- RAGAS provides standard vocabulary for technical interviews; custom metric provides legal-domain defensibility

**Negative / Watch:**
- 100-case labelling is 2–3 days of focused work — schedule this explicitly in Week 3
- RAGAS requires a judge LLM to evaluate faithfulness — this adds a small eval cost (acceptable; eval runs once per week, not per query)
- RAGAS and custom citation metric may produce apparently contradictory results on edge cases — resolve by treating citation precision as the primary metric for legal product quality

---

## Alternatives Rejected

- **Option A (RAGAS only):** Rejected. Does not catch correct-answer/wrong-citation failures — the defining failure mode for a legal citation product.
- **Option B (custom only):** Rejected. No standard vocabulary for technical interviews; RAGAS faithfulness is a more reliable hallucination detector than a hand-written regex detector.
