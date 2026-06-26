# ADR-006 — Backend Framework and Async Ingestion Pattern

**Date:** 2026-06-26
**Status:** Accepted
**Author:** Mehtab Singh
**Decider:** Mehtab Singh
**Depends on:** ADR-004 (LLM cascade), ADR-005 (extraction framework)

---

## Context

Nyaya AI needs a backend that handles:
1. **File upload** — PDF/DOCX contracts, potentially large and slow to process
2. **Async ingestion pipeline** — OCR (PaddleOCR on scanned documents) + structural chunking + embedding (BGE-M3) + Qdrant indexing takes 10–60 seconds depending on document size and quality
3. **LLM inference** — synchronous request/response for Mode 1 risk scan results and Mode 2 chat turns
4. **Streaming responses** — Mode 2 chat answers should stream token-by-token for UX
5. **Session state** — Mode 2 conversation memory must persist across chat turns within a session

A synchronous API that blocks on ingestion will timeout on large contracts and produce a broken UX. The backend must decouple upload from processing.

---

## Decision Question (as posed)

> **What serves the API layer for Nyaya AI?**
>
> **Option A — FastAPI**
> Modern async Python framework. Native async/await. OpenAPI docs auto-generated. Pydantic-native.
> | Why choose it | Tradeoff |
> |---|---|
> | Async-native for LLM streaming; Pydantic integration seamless; production-grade | More setup than Streamlit; you write the API yourself |
>
> **Option B — FastAPI + Celery + Redis**
> FastAPI for the API layer, Celery for background task queue, Redis as the broker.
> | Why choose it | Tradeoff |
> |---|---|
> | Ingestion offloaded to background worker — API never blocks on upload | More infra to manage (Redis + Celery worker); overkill if ingestion is fast enough |
>
> **Option C — Flask**
> Simpler synchronous framework.
> | Why choose it | Tradeoff |
> |---|---|
> | Less setup; widely known | Synchronous by default — LLM calls and streaming need workarounds; Pydantic not native |
>
> **Option D — Streamlit (backend + frontend in one)**
> Upload widget, results display, and chat interface all in Streamlit. No separate API.
> | Why choose it | Tradeoff |
> |---|---|
> | Fastest to build a demo | Not production architecture; no proper API; cannot support async ingestion; looks like a demo |
>
> **Agent recommendation:** Option B

---

## Decision

**FastAPI + Celery + Redis.**

Redis serves a dual purpose — deliberately:
1. **Celery broker** — task queue for background ingestion jobs
2. **Session store** — Mode 2 conversation memory, scoped per session UUID

---

## Request Flows

### Mode 1 — Contract Upload and Scan

```
POST /upload
  │
  ├─ Validate file type and size
  ├─ Assign job_id (UUID)
  ├─ Store file to local storage
  ├─ Enqueue Celery task: ingest_contract(job_id, file_path)
  └─ Return { job_id, status: "queued" }  ← immediate response

Celery Worker (background):
  ingest_contract(job_id)
  │
  ├─ Parse PDF/DOCX (PyMuPDF / Unstructured.io)
  ├─ OCR if scanned (PaddleOCR)
  ├─ Structural chunking → LLM fallback chunking if needed
  ├─ Embed chunks (BGE-M3 via FastEmbed)
  ├─ Index into nyaya_contracts (Qdrant)
  ├─ Run risk scan engines (ICA §27, MSME, etc.)
  ├─ Validate outputs (Pydantic)
  └─ Store results to Redis: results:{job_id}

GET /status/{job_id}
  │
  ├─ Check Redis for results:{job_id}
  ├─ If pending → { status: "processing" }
  └─ If ready → { status: "complete", results: RiskScanReport }
```

### Mode 2 — Legal Intelligence Chat

```
POST /chat
  body: { session_id, message, document_id? }
  │
  ├─ Retrieve conversation history from Redis: session:{session_id}
  ├─ Build retrieval query from message + history
  ├─ Hybrid retrieval from nyaya_corpus (always)
  │   + nyaya_contracts if document_id provided
  ├─ Rerank with bge-reranker-large
  ├─ Run LLM cascade → CitedAnswer (Pydantic)
  ├─ Append turn to Redis: session:{session_id}
  └─ Stream response via Server-Sent Events (SSE)
```

---

## API Endpoints (FastAPI)

```python
POST   /upload                    # upload contract, returns job_id
GET    /status/{job_id}           # poll ingestion + scan status
GET    /results/{job_id}          # full risk scan report
POST   /diff                      # upload 2 contracts, return semantic diff
POST   /chat                      # chat turn (Mode 2), streams SSE
DELETE /session/{session_id}      # clear conversation memory
POST   /corpus/ingest             # admin: add a new Act to nyaya_corpus
GET    /health                    # health check
```

All request/response bodies are Pydantic-validated. OpenAPI docs auto-generated at `/docs`.

---

## Why Redis Serves Dual Purpose

Two separate infrastructure components (a dedicated message broker like RabbitMQ + a separate session store like Memcached) would solve the same problems. Redis handles both because:

1. Redis is already a first-class Celery broker — no workarounds, well-documented, production-tested
2. Redis key-value store is the natural fit for session state: `session:{uuid}` → serialised conversation history as JSON, with TTL expiry (24h default)
3. One infrastructure component = one thing to deploy, monitor, and maintain

The dual use is not a hack. It is a deliberate architectural decision to keep the stack lean for a product at this stage.

---

## Why Streamlit Was Considered and Rejected

Streamlit can produce a working demo of Nyaya AI in ~2 days. That is its strength and the reason it was considered.

**Rejection reasons:**

1. **No async ingestion support.** Streamlit runs in a single-threaded execution model per user session. A Celery worker queue cannot be integrated cleanly. Long-running ingestion would block the entire Streamlit app for that user.

2. **No proper API.** Streamlit has no REST API layer. If the product ever needs a mobile client, a WhatsApp bot integration (planned bonus feature), or a third-party integration, there is no API to call.

3. **Not a production architecture.** Streamlit is a prototyping tool. This product is explicitly designed to demonstrate production engineering competence — to SpotDraft, Sarvam AI, Razorpay. A Streamlit UI signals "demo" to every technical interviewer at those companies.

4. **Cannot support streaming chat.** Server-Sent Events (SSE) for streaming Mode 2 responses require proper HTTP infrastructure. Streamlit has no native SSE support.

The correct time to use Streamlit is for a rapid internal prototype to validate a concept. That time has passed — the concept is validated by the problem statement and design doc. The architecture must now be production-quality.

---

## Consequences

**Positive:**
- API never blocks on file upload — UX is immediate
- Ingestion pipeline runs as a background Celery worker — can be scaled independently
- Redis dual-use keeps the infrastructure footprint minimal
- FastAPI + Pydantic integration is seamless — extraction schemas from ADR-005 are the API response schemas
- OpenAPI docs auto-generated — mentor and interviewer can see the full API surface at `/docs`

**Negative / Watch:**
- Redis is now a critical dependency — if Redis goes down, both the task queue and all active chat sessions fail. Redis must be deployed with persistence enabled (`appendonly yes`).
- Celery adds worker process management — monitor via Flower (Celery monitoring dashboard) in Week 4
- SSE streaming for Mode 2 requires the frontend to handle `EventSource` correctly

---

## Alternatives Rejected

- **Option A (FastAPI only):** Rejected. Synchronous ingestion blocks the API endpoint and will timeout on large contracts.
- **Option C (Flask):** Rejected. Synchronous by default; Pydantic not native; no async streaming support.
- **Option D (Streamlit):** Rejected. Cannot support async ingestion, has no REST API, cannot support streaming chat. See detailed rejection reasoning above.
