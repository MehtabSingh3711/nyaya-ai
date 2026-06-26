# ADR-009 — Observability and Tracing

**Date:** 2026-06-26
**Status:** Accepted
**Author:** Mehtab Singh
**Decider:** Mehtab Singh
**Depends on:** ADR-004 (LLM cascade), ADR-006 (FastAPI + Celery backend), ADR-008 (evaluation framework)

---

## Context

Nyaya AI is a multi-step pipeline: file upload → OCR → chunking → embedding → retrieval → LLM cascade → Pydantic validation → structured output. When something goes wrong — a wrong citation, an unexpected "I don't know," a slow response — the system must be able to explain what happened at every step.

Two categories of observability are needed:
1. **LLM layer** — what model was called, with what prompt, what came back, how many tokens, how long it took, did the cascade escalate, did cite-or-refuse fire
2. **Application layer** — Celery task lifecycle, OCR quality, chunk count, retrieval results, validation failures, ingestion timing

These are different questions requiring different tools. A single tool that tries to answer both tends to answer neither well.

---

## Decision Question (as posed)

> **How do you see what the system is doing in production?**
>
> **Option A — Langfuse only**
> Open-source LLM observability. Traces every LLM call. Self-hostable.
> | Why choose it | Tradeoff |
> |---|---|
> | Purpose-built for LLM tracing; integrates with RAGAS; free self-hosted | Does not cover application-layer events (Celery tasks, ingestion pipeline steps) |
>
> **Option B — Langfuse + structlog**
> Langfuse for LLM traces. `structlog` for application-level structured JSON logs.
> | Why choose it | Tradeoff |
> |---|---|
> | Each layer answers different questions; both are searchable independently | Two systems to set up; discipline required to log consistently |
>
> **Option C — OpenTelemetry**
> Industry-standard distributed tracing. Full trace from HTTP request to LLM response.
> | Why choose it | Tradeoff |
> |---|---|
> | Full distributed trace; standard tooling | Significant setup complexity; overkill for a single-developer 5-week project |
>
> **Agent recommendation:** Option B

---

## Decision

**Langfuse + structlog — two complementary observability layers.**

---

## Layer 1: Langfuse (LLM Layer)

**Deployed as:** self-hosted Langfuse instance in Docker alongside the app (`docker-compose.yml` includes Langfuse + Postgres backend)

**What Langfuse traces:**

Every Mode 1 scan and every Mode 2 chat session is a Langfuse **trace**. Each step within that trace is a **span**.

```
Trace: ingest_and_scan (Mode 1)
  ├── Span: parse_document         {file_type, page_count, ocr_used: bool}
  ├── Span: chunk_document         {chunk_count, strategy: "structural"|"llm_fallback"}
  ├── Span: embed_chunks           {model: "BGE-M3", duration_ms, chunk_count}
  ├── Span: retrieve               {collection, top_k, similarity_scores[]}
  ├── Span: rerank                 {model: "bge-reranker-large", scores[]}
  └── Span: llm_cascade
        ├── Span: tier_1_call      {model: "phi3-mini", tokens_in, tokens_out, latency_ms, confidence}
        ├── Span: tier_2_call?     {model: "gemma2-9b", escalation_reason, ...}  ← only if escalated
        └── Span: tier_3_call?     {model: "openrouter/*", escalation_reason, ...}

Trace: chat_turn (Mode 2)
  ├── Span: retrieve_corpus        {query, top_k, collection: "nyaya_corpus", scores[]}
  ├── Span: retrieve_contract?     {query, top_k, collection: "nyaya_contracts", session_id}
  ├── Span: rerank                 {combined_results, final_top_k}
  └── Span: llm_cascade
        └── [same span structure as above]
```

**RAGAS scores attached to traces:**
After eval runs, RAGAS `faithfulness` and `answer_relevance` scores are attached to the corresponding trace as Langfuse **scores**. This makes eval results queryable by session, by contract type, by difficulty.

```python
langfuse.score(
    trace_id=trace_id,
    name="ragas_faithfulness",
    value=ragas_result["faithfulness"],
    comment=f"test_case_id={test_case.id}, difficulty={test_case.difficulty}"
)
```

---

## Layer 2: structlog (Application Layer)

**Format:** Structured JSON — every log line is a JSON object with a consistent schema. Queryable with `jq`, Loki, or any log aggregator.

**What structlog logs:**

### Five Mandatory Event Types (non-negotiable — these must be logged on every occurrence)

#### 1. Cascade Escalation
```json
{
  "event": "cascade_escalation",
  "tier_from": 1,
  "tier_to": 2,
  "reason": "confidence_below_threshold",
  "confidence_score": 0.54,
  "threshold": 0.70,
  "query_id": "uuid",
  "contract_id": "uuid",
  "model_from": "phi3-mini",
  "model_to": "gemma2-9b",
  "timestamp": "2026-07-01T10:32:44Z"
}
```

#### 2. Cite-or-Refuse Trigger
```json
{
  "event": "cite_or_refuse_triggered",
  "query": "Is the liability clause enforceable?",
  "final_confidence": 0.41,
  "tier_reached": 3,
  "retrieved_chunks": 3,
  "top_similarity_score": 0.61,
  "refusal_reason": "evidence_below_threshold",
  "query_id": "uuid",
  "session_id": "uuid",
  "timestamp": "2026-07-01T10:33:01Z"
}
```

#### 3. Pydantic Validation Failure
```json
{
  "event": "pydantic_validation_failure",
  "schema": "RiskFinding",
  "tier": 1,
  "raw_output": "<truncated LLM output>",
  "validation_error": "field 'clause_number' missing",
  "action": "retry_same_tier",
  "retry_count": 1,
  "query_id": "uuid",
  "timestamp": "2026-07-01T10:33:15Z"
}
```

#### 4. OCR Fallback Trigger
```json
{
  "event": "ocr_fallback_triggered",
  "contract_id": "uuid",
  "reason": "no_structural_markers_detected",
  "ocr_engine": "PaddleOCR",
  "page_count": 12,
  "ocr_confidence_mean": 0.83,
  "timestamp": "2026-07-01T10:31:02Z"
}
```

#### 5. Cross-Collection Retrieval Merge
```json
{
  "event": "cross_collection_merge",
  "session_id": "uuid",
  "corpus_chunks_retrieved": 3,
  "contract_chunks_retrieved": 2,
  "merge_strategy": "interleave_by_score",
  "final_top_k": 5,
  "timestamp": "2026-07-01T10:33:20Z"
}
```

### Additional Standard Application Events

```json
{"event": "celery_task_started", "task_id": "...", "contract_id": "...", "file_size_kb": 240}
{"event": "celery_task_complete", "task_id": "...", "duration_ms": 18400, "chunk_count": 43}
{"event": "celery_task_failed", "task_id": "...", "error": "PaddleOCR timeout", "traceback": "..."}
{"event": "qdrant_index_complete", "collection": "nyaya_contracts", "vectors_added": 43, "duration_ms": 1200}
{"event": "retrieval_complete", "collection": "nyaya_corpus", "top_k": 5, "scores": [0.91, 0.87, 0.82, 0.79, 0.71]}
{"event": "embedding_complete", "model": "BGE-M3", "chunk_count": 43, "duration_ms": 3400}
```

---

## Why These Five Events Are Non-Negotiable

> "These are the events that explain system behaviour when something goes wrong — and they are also the events that make the architecture review session with the mentor demonstrable, not just describable."

Each mandatory event answers a specific diagnostic question:

| Event | Diagnostic question |
|---|---|
| `cascade_escalation` | Why did this query cost more? Which tier handled it and why? |
| `cite_or_refuse_triggered` | Why did the system say "I don't know"? Was the retrieved context genuinely weak? |
| `pydantic_validation_failure` | Where is the LLM producing malformed output? Which tier, which schema field? |
| `ocr_fallback_triggered` | Which contracts are hitting the LLM chunker? Is OCR quality a systematic problem? |
| `cross_collection_merge` | When Mode 2 queries both corpus and contract, how are the results merging? |

Without these logs, debugging requires adding instrumentation after the fact — always slower than having it from the start.

---

## Deployment

```yaml
# docker-compose.yml (excerpt)
services:
  langfuse:
    image: langfuse/langfuse:latest
    ports: ["3000:3000"]
    environment:
      DATABASE_URL: postgresql://...
      NEXTAUTH_SECRET: ...

  langfuse-db:
    image: postgres:15
    volumes: ["langfuse_db:/var/lib/postgresql/data"]

  app:
    environment:
      LANGFUSE_PUBLIC_KEY: ...
      LANGFUSE_SECRET_KEY: ...
      LANGFUSE_HOST: http://langfuse:3000
```

structlog outputs to stdout in development (human-readable with colour). In production (Docker), stdout is captured as structured JSON by the container runtime log driver.

---

## Why OpenTelemetry Was Considered and Rejected

OpenTelemetry is the correct observability answer for a microservices architecture with multiple deployed services, distributed tracing across service boundaries, and a team of engineers who need a unified trace view.

Nyaya AI at this stage is:
- One FastAPI process
- One Celery worker process
- One Langfuse instance
- All on the same Docker network

Setting up an OTel collector, a Jaeger or Tempo backend, and the full instrumentation pipeline for these three processes adds approximately 1–2 days of setup with no material observability benefit over Langfuse + structlog. The same diagnostic questions are answered more cheaply.

OpenTelemetry is the right addition **when** the platform adds a second backend service (e.g. a separate corpus management service, a dedicated eval runner). At that point, distributed tracing becomes necessary. The architecture should be designed to allow OTel to be bolted on — using standard HTTP headers, not bespoke correlation IDs — but it does not need to be implemented now.

---

## Consequences

**Positive:**
- Every LLM call visible in Langfuse with full prompt/response/latency/tokens
- Every cascade escalation and cite-or-refuse event logged and queryable
- RAGAS scores attached to production traces — eval is not a separate offline process
- Langfuse is self-hosted — no data leaves the infra
- structlog JSON is queryable with `jq` locally or piped to any log aggregator later

**Negative / Watch:**
- Langfuse self-hosted requires a Postgres instance — adds to Docker Compose resource usage
- Discipline required to log all five mandatory events consistently — add a code review checklist item
- structlog JSON volume can be high on ingestion of large contracts — set log rotation policy

---

## Alternatives Rejected

- **Option A (Langfuse only):** Rejected. Does not cover application-layer events — Celery task lifecycle, ingestion pipeline steps, retrieval results are invisible without structured application logs.
- **Option C (OpenTelemetry):** Rejected — correct at production scale, wrong for a 5-week single-developer project. Can be added post-internship when the platform adds more services.
