# ADR-005 — Structured Extraction Framework

**Date:** 2026-06-26
**Status:** Accepted
**Author:** Mehtab Singh
**Decider:** Mehtab Singh
**Depends on:** ADR-004 (LLM cascade design)

---

## Context

Nyaya AI's Mode 1 (Automatic Scan) must convert retrieved contract text into validated, typed structured output — risk findings, extracted clauses, MSME violations, etc. Every output that reaches the user must be schema-valid: the right fields present, the right types, within the right ranges. An unvalidated free-text blob from an LLM is not acceptable output for a legal platform.

The extraction framework must integrate with the LLM cascade (ADR-004): when a tier fails to produce valid output, the failure should trigger the same escalation logic as a low confidence score.

---

## Decision Question (as posed)

> **How does Mode 1 convert retrieved contract text into validated, typed JSON output?**
>
> **Option A — Pydantic v2 + JSON mode**
> Define a Pydantic model for each extraction type. Prompt the LLM with the schema. Use JSON mode (Ollama/OpenAI-compatible) to force valid JSON. Validate with Pydantic — invalid output triggers retry or escalation.
> | Why choose it | Tradeoff |
> |---|---|
> | Type-safe, validated output; schemas are the source of truth; retry logic is explicit | LLMs occasionally produce structurally valid JSON that is semantically wrong; retry adds latency |
>
> **Option B — Function calling / tool use**
> Define extraction as a tool call. The LLM calls the tool with structured arguments.
> | Why choose it | Tradeoff |
> |---|---|
> | Clean integration with OpenAI-format APIs | Ollama function calling support varies by model; inconsistent on Phi-3 Mini / Gemma-2-9B |
>
> **Option C — Instructor library (Pydantic + retry wrapper)**
> `Instructor` wraps any OpenAI-compatible LLM with automatic Pydantic validation and retry. One decorator, fully automatic.
> | Why choose it | Tradeoff |
> |---|---|
> | Eliminates manual retry logic; less boilerplate | Abstraction hides failure modes; retry decisions are not in our control |
>
> **Agent recommendation:** Option A

---

## Decision

**Pydantic v2 + JSON mode, with explicit retry and escalation logic.**

- Define a Pydantic model for each extraction type
- Prompt the LLM with the schema (field names, types, and descriptions inline in the system prompt)
- Use Ollama's OpenAI-compatible endpoint with `format="json"` to constrain output
- Validate every response with Pydantic on receipt
- **On validation failure:** one retry at the same cascade tier
- **On second failure:** escalate to the next cascade tier (same logic as a low confidence score)
- Retry and escalation decisions remain explicit in application code — not abstracted

---

## Extraction Schemas (Pydantic Models)

```python
# Risk finding — output of ICA §27 engine, MSME detector, etc.
class RiskFinding(BaseModel):
    clause_number: str                        # e.g. "12.3"
    clause_heading: Optional[str]
    clause_text: str                          # verbatim extracted text
    page: int
    paragraph: Optional[int]
    risk_type: Literal[
        "non_compete", "payment_term_violation",
        "uncapped_liability", "broad_ip_assignment",
        "auto_renewal", "broad_indemnity", "other"
    ]
    risk_level: Literal["high", "medium", "low"]
    legal_basis: str                          # e.g. "Indian Contract Act §27"
    finding: str                              # plain-language explanation
    negotiation_stance: str                   # what to push back on
    confidence: float                         # 0.0–1.0, LLM self-assessed

# Structured fields extracted from the contract header / body
class ClauseExtraction(BaseModel):
    parties: List[str]
    governing_law: Optional[str]
    effective_date: Optional[str]
    term_months: Optional[int]
    termination_notice_days: Optional[int]
    liability_cap: Optional[str]
    payment_term_days: Optional[int]
    has_non_compete: bool
    has_ip_assignment: bool
    has_arbitration_clause: bool

# MSME-specific violation output
class MSMEViolation(BaseModel):
    clause_number: str
    clause_text: str
    page: int
    payment_term_days: int                    # the stated term
    violation: str                            # plain-language violation description
    statutory_remedy: str                     # what the MSME Act allows
    legal_basis: str                          # "MSME Development Act 2006, §15-23"
    confidence: float

# Mode 2 chat response
class CitedAnswer(BaseModel):
    answer: str                               # plain-language answer
    citations: List[Citation]                 # list of sources
    confidence: float
    can_answer: bool                          # False = cite-or-refuse path

class Citation(BaseModel):
    source_type: Literal["statute", "contract"]
    act_name: Optional[str]                   # e.g. "Indian Contract Act 1872"
    section: Optional[str]                    # e.g. "§27"
    clause_number: Optional[str]              # for contract citations
    page: Optional[int]
    quote: str                                # verbatim passage cited
```

---

## Retry and Escalation Logic

```
LLM response received
        │
        ▼
Pydantic validation
        │
   ┌────┴────┐
   │ Valid?  │
   └────┬────┘
    No  │  Yes
        │   └──→ Check confidence score
        ▼               │
   Retry at         < threshold?
   same tier            │
        │           Yes │  No
        ▼               ▼   └──→ Return to caller
Pydantic validation  Escalate
        │            to next tier
   ┌────┴────┐
   │ Valid?  │
   └────┬────┘
    No  │  Yes
        ▼   └──→ Check confidence score
   Escalate
   to next tier
        │
  (if Tier 3 fails both validations)
        ▼
   Cite-or-refuse output
```

Schema validation failure is treated identically to a low confidence score. Both are signals that the current tier cannot handle the query. The cascade makes no distinction between "I produced invalid JSON" and "I produced valid JSON with low confidence" — both escalate.

---

## Why Instructor Was Considered and Rejected

`Instructor` (by Jason Liu) is an excellent library that wraps any OpenAI-compatible LLM with automatic Pydantic validation and retry. It would eliminate the manual retry logic above.

**Reason for rejection:**

The retry decision is not just a convenience — it is an integral part of the LLM cascade designed in ADR-004. When a tier produces invalid output, the decision to retry vs. escalate depends on context: which tier we are on, how many retries have already been attempted, what the confidence score is. `Instructor` handles retry automatically, with its own internal logic, behind an abstraction boundary.

Keeping this logic explicit in application code means:
1. Langfuse can trace every retry and escalation decision as a distinct event
2. The threshold can be tuned independently of the library version
3. A future change to the cascade design (e.g. adding a Tier 1.5, or changing retry count by tier) does not require understanding Instructor internals

The boilerplate cost is low — the retry logic is ~30 lines of code. The control benefit is high.

---

## Consequences

**Positive:**
- Every extracted field is type-validated before it reaches the user
- Schema validation failures are handled identically to confidence failures — consistent cascade behaviour
- All retry and escalation decisions are visible in application code and traceable in Langfuse
- Pydantic schemas are the single source of truth for output structure — documentation and validation in one place

**Negative / Watch:**
- LLMs can produce structurally valid JSON that is semantically wrong (e.g. `confidence: 0.95` when the answer is actually weak) — Pydantic catches schema errors but not semantic errors; the eval harness catches the latter
- Retry at the same tier adds latency on failure paths — acceptable given the 80–90% first-pass success rate targeted

---

## Alternatives Rejected

- **Option B (function calling):** Rejected. Phi-3 Mini and Gemma-2-9B function calling support via Ollama is inconsistent — not reliable enough for production extraction.
- **Option C (Instructor):** Rejected specifically to keep retry and escalation logic transparent and under our control. See reasoning above.
