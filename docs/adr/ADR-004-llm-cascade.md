# ADR-004 — LLM Cascade Design and Cost Architecture

**Date:** 2026-06-26
**Status:** Accepted
**Author:** Mehtab Singh
**Decider:** Mehtab Singh
**Depends on:** ADR-002 (embedding model), ADR-003 (vector DB)

---

## Context

Nyaya AI requires an LLM for three classes of work:
1. **Structured extraction** — extracting parties, dates, governing law, payment terms, clause numbers from contract text (relatively simple, deterministic)
2. **Risk classification** — classifying retrieved clauses into risk levels, flagging against known legal patterns (MSME Act, ICA §27)
3. **Complex legal reasoning** — explaining *why* a clause is risky, generating negotiation stances, handling ambiguous contract language, answering nuanced legal questions in Mode 2

The system needs different capability levels for each class. Running GPT-4o on every query would be expensive and unnecessary. Running Phi-3 Mini on complex legal reasoning would produce low-quality, potentially hallucinated output.

The target in AGENTS.md was < ₹0.50 per contract at p95. This decision supersedes that target.

---

## Decision Question (as posed)

> **How does the system decide which LLM to use for a given query, and what triggers escalation?**
>
> **Option A — Fixed tier assignment by task type**
> Assign each task class permanently to a tier: simple extraction → Phi-3 Mini always; risk classification → Gemma-2-9B always; complex legal reasoning → GPT-4o always. No dynamic escalation.
> | Why choose it | Tradeoff |
> |---|---|
> | Predictable cost per query type; simple to implement | No adaptation — a simple contract hits GPT-4o for all risk analysis even if it's obvious |
>
> **Option B — Confidence-threshold cascade (dynamic)**
> Every query starts at Phi-3 Mini. The output includes a confidence score. If score < threshold → escalate to Gemma-2-9B. If still < threshold → escalate to GPT-4o. Cite-or-refuse if GPT-4o is also below threshold.
> | Why choose it | Tradeoff |
> |---|---|
> | Minimises cost — 80–90% of queries resolved at Tier 1; escalation is rare | Requires a reliable confidence signal; threshold calibration needed |
>
> **Option C — Hybrid: fixed assignment + confidence override**
> Fixed tier assignment by task class, with a confidence override to escalate one tier if needed.
> | Why choose it | Tradeoff |
> |---|---|
> | Predictable baseline; safety valve for hard cases | Complex tasks always start expensive |
>
> **Option D — Router model (meta-LLM)**
> A tiny classifier reads the query and retrieved context, predicts which LLM tier is needed, and routes directly.
> | Why choose it | Tradeoff |
> |---|---|
> | Single LLM call per query | Router accuracy must be very high; adds a model to maintain |
>
> **Agent recommendation:** Option B

---

## Decision

**Option B — Confidence-threshold cascade, with a fully free local stack.**

| Tier | Model | Runtime | Cost | Trigger |
|------|-------|---------|------|---------|
| Tier 1 | Phi-3 Mini (3.8B) | Ollama, local | ₹0 | All queries start here |
| Tier 2 | Gemma-2-9B | Ollama, local | ₹0 | Confidence < threshold after Tier 1 |
| Tier 3 | OpenRouter free tier | Online API | ₹0 | Confidence < threshold after Tier 2 |
| Refuse | — | — | ₹0 | Confidence < threshold after Tier 3 |

**Cost per contract: ₹0.**

---

## Reasoning

### Why Option B (cascade) over the alternatives

80–90% of contract queries are simple: "extract the governing law clause," "is there a payment term in this clause," "what is the termination notice period." A small local model handles these correctly and instantly. Routing every query to a large model wastes capacity on easy cases. The cascade ensures that only genuinely hard queries — ambiguous clause language, complex ICA §27 analysis, nuanced Mode 2 follow-up questions — consume the more capable models.

### Why fully local + free (the critical product decision)

The original architecture targeted < ₹0.50 per contract. This decision supersedes that target with ₹0.

This is not a cost-optimisation decision. It is a **product philosophy decision**:

> Nyaya AI serves users who cannot afford paid legal tools. A ₹50,000 lawyer review is inaccessible to them. The platform exists to close that gap. A system that carries per-query API costs — even small ones — creates a structural pressure toward monetisation that eventually prices out the users it was built for. The platform must be free to operate, not as a growth tactic, but because the mission requires it.

**Tier 1 — Phi-3 Mini via Ollama (local)**
Microsoft's Phi-3 Mini (3.8B parameters) performs comparably to much larger models on structured tasks. It runs on a CPU with ~6GB RAM via Ollama. No API call, no rate limit, no cost. This is the correct model for extraction and simple classification.

**Tier 2 — Gemma-2-9B via Ollama (local)**
Google's Gemma-2-9B is a capable mid-tier model that handles more complex reasoning than Phi-3 Mini. Runs locally via Ollama with a GPU (≥ 10GB VRAM) or slowly on CPU. Handles the majority of risk classification and most Mode 2 legal questions.

**Tier 3 — OpenRouter free tier (online fallback)**
For genuinely hard queries that neither local model handles with sufficient confidence, OpenRouter provides access to capable models (including open-source alternatives to GPT-4o) on a free tier. This is a last-resort online fallback — it handles a small fraction of queries, involves an API call, and is the only point where data leaves the local stack. This is acceptable because:
- It is triggered only when both local models have already failed
- The query + retrieved context going to OpenRouter is already a processed, anonymised payload — not the raw contract
- The free tier has sufficient capacity for a product at this stage

**Cite-or-refuse remains the final gate.** If Tier 3 also returns a confidence-below-threshold output, the system outputs "I don't know" with an explanation of what it could and could not find. No answer is better than a wrong one in a legal product.

---

## Confidence Score Implementation Note

The confidence signal is derived from:
1. **Retrieval confidence** — the reranker score from bge-reranker-large on the top retrieved chunk. Low reranker score = weak evidence = escalate.
2. **LLM self-assessment** — the model is prompted to include a confidence field in its structured JSON output (0.0–1.0). This is a heuristic, not a calibrated probability, and will be calibrated against the eval set in Week 3.
3. **Cite-or-refuse threshold** — tuned on the 100-question eval set. Starting value: 0.7. Adjust after first eval run.

---

## Consequences

**Positive:**
- Cost per contract = ₹0 — fully free to operate
- No vendor dependency for the primary path (Tiers 1 and 2 are fully local)
- No rate limits on 80–90% of queries
- No data egress on 80–90% of queries (local inference)
- Confidence cascade is auditable — every escalation decision is logged in Langfuse

**Negative / Watch:**
- Ollama requires sufficient local RAM/VRAM — development: developer laptop + Colab; production: Railway instance with appropriate resource allocation
- Tier 3 (OpenRouter) requires network access and introduces latency on the escalation path (~1–3s additional)
- Confidence score calibration is deferred to Week 3 — initial thresholds are heuristic
- OpenRouter free tier has rate limits — monitor usage if query volume grows

---

## Alternatives Rejected

- **Option A (fixed assignment):** Rejected. Sends all risk classification to Gemma-2-9B and all complex reasoning to GPT-4o regardless of difficulty — over-spends on easy queries.
- **Option C (fixed + override):** Rejected in favour of B. Same over-assignment problem as A on the primary path.
- **Option D (router model):** Rejected. Adds model maintenance overhead; router accuracy risk is high at this stage.
- **Paid API tiers (OpenAI, Anthropic, Cohere):** Rejected. Per-query cost creates structural pressure toward monetisation inconsistent with the product mission.
