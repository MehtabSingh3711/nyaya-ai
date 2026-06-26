# AI Session Log — 2026-06-25 — Architecture Document

**Agent:** Antigravity (Claude Sonnet 4.6 — Thinking)
**Phase:** Week 1 — Foundation
**Session opened:** 18:54 IST

## Session Goal

Make all architecture decisions through the decision protocol, log every one, then write `/docs/architecture.md` (due 26 June).

## Decisions Log

### Decision 1: Document Chunking Strategy
**Options presented:** A (structural), B (sliding window), C (structural + sliding fallback), D (structural + LLM fallback)
**Student chose:** Structural chunking primary; LLM-based structural chunking as fallback for poorly-formatted / scanned documents
**Student's reason:** LLM fallback gives full accuracy even on bad OCR/scanned contracts; specific LLM for chunking to be sourced from niche GitHub repos later
**Agent recommendation was:** Option C (structural + sliding window fallback)
**Student followed agent recommendation:** No — upgraded the fallback from sliding window to LLM-based structural detection
**Logged at:** 2026-06-26, 16:23 IST
**ADR:** ADR-001

### Decision 2: Embedding Model
**Options presented:** A (BGE-M3 local), B (OpenAI text-embedding-3), C (Voyage voyage-law-2), D (Cohere multilingual-v3)
**Student chose:** Option A — BGE-M3, running locally via HuggingFace + Qdrant FastEmbed; bge-reranker-large added as cross-encoder reranking layer
**Student's reason:** API-only models (Voyage, OpenAI, Cohere) ruled out — data leaves infra, ongoing cost on reindexing, no local control. BGE-M3 covers multilingual, runs locally, zero reindexing cost. Citation precision gap addressed by bge-reranker-large at rerank layer.
**Agent recommendation was:** Option A (BGE-M3)
**Student followed agent recommendation:** Yes — and extended it with explicit reranker choice
**Logged at:** 2026-06-26, 16:37 IST
**ADR:** ADR-002

### Decision 3: Vector Database Collection Architecture
**Options presented:** A (single collection), B (two collections), C (two collections + named vectors for native hybrid search)
**Student chose:** Option C — two collections (nyaya_corpus + nyaya_contracts) with named vectors (dense BGE-M3 + sparse SPLADE) per chunk
**Student's reason:** Direct consequence of the hybrid retrieval decision — named vectors implement BM25+dense hybrid in a single Qdrant query without application-layer merging. Cross-collection queries merge at application layer only.
**Agent recommendation was:** Option C
**Student followed agent recommendation:** Yes
**Logged at:** 2026-06-26, 16:45 IST
**ADR:** ADR-003

### Decision 4: LLM Cascade Design
**Options presented:** A (fixed tier by task), B (confidence-threshold cascade), C (hybrid fixed+override), D (router model)
**Student chose:** Option B — confidence-threshold cascade. Modified stack: Tier 1 = Phi-3 Mini via Ollama (local), Tier 2 = Gemma-2-9B via Ollama (local), Tier 3 = OpenRouter free tier (online last resort). Fully free end-to-end.
**Student's reason:** Fully free architecture is a deliberate product decision — Nyaya AI serves users who cannot afford paid legal tools; a platform built for them should not carry per-query API costs. Cost per contract = ₹0.
**Agent recommendation was:** Option B
**Student followed agent recommendation:** Yes — and extended it with a fully-local-free stack replacing paid API tiers
**Logged at:** 2026-06-26, 17:00 IST
**ADR:** ADR-004

### Decision 5: Structured Extraction Framework
**Options presented:** A (Pydantic v2 + JSON mode), B (function calling), C (Instructor library)
**Student chose:** Option A — Pydantic v2 + JSON mode. One retry at same tier on validation failure, second failure escalates to next cascade tier. Retry/escalation logic stays explicit in code.
**Student's reason:** Schema validation failure is treated identically to low confidence score — both signal the current tier cannot handle the query. Keeping retry and escalation logic visible keeps the cascade transparent. Instructor rejected specifically to avoid hiding failure modes.
**Agent recommendation was:** Option A
**Student followed agent recommendation:** Yes — and added the explicit connection between schema failure and cascade escalation
**Logged at:** 2026-06-26, 17:04 IST
**ADR:** ADR-005

### Decision 6: Backend Framework
**Options presented:** A (FastAPI), B (FastAPI + Celery + Redis), C (Flask), D (Streamlit)
**Student chose:** Option B — FastAPI + Celery + Redis. Redis serves dual purpose: Celery broker + Mode 2 session store. Flow: upload → job_id → worker ingests → frontend polls /status/{job_id}.
**Student's reason:** Contract ingestion is too slow for a synchronous endpoint. Dual Redis usage keeps stack lean — one infra component solving two problems. Streamlit rejected: demo not product, cannot support async ingestion pattern.
**Agent recommendation was:** Option B
**Student followed agent recommendation:** Yes — and added the dual-use Redis rationale explicitly
**Logged at:** 2026-06-26, 17:21 IST
**ADR:** ADR-006

### Decision 7: Frontend Framework and Visual Standard
**Options presented:** A (Next.js), B (Next.js + shadcn/ui), C (Vite + React), D (HTMX + Jinja2)
**Student chose:** Option B — Next.js + shadcn/ui. Dark/deep navy theme. Two-panel layout (scan left, chat right). All shadcn components customised to Nyaya AI brand. Aesthetic quality is a product requirement.
**Student's reason:** Users will not trust a legal tool that looks unpolished. Visual register: linear.app / Perplexity AI. Functional requirements are non-negotiable (drag-drop, polling, SSE, citation sidebar, risk panel, confidence display, cite-or-refuse state).
**Agent recommendation was:** Option B
**Student followed agent recommendation:** Yes — and elevated visual quality to a hard product requirement with specific functional requirements listed
**Logged at:** 2026-06-26, 17:28 IST
**ADR:** ADR-007

### Decision 8: Evaluation Framework
**Options presented:** A (RAGAS only), B (custom eval harness only), C (RAGAS + custom citation metric)
**Student chose:** Option C. 100 Q&A pairs minimum, difficulty-tagged (simple extraction / risk classification / complex legal reasoning), all six contract types, both modes. Four targets measured explicitly: citation precision (custom metric), hallucination rate (RAGAS faithfulness), extraction F1 (field-level), cost per contract (Langfuse token logging). All four on live eval dashboard in frontend. Labelling in Week 3.
**Student's reason:** RAGAS alone misses wrong-clause-right-answer failures — a system that gives correct answers with wrong citations is a legal product failure, not a minor inaccuracy. Difficulty breakdown matters: 92% overall vs even performance across difficulty levels are different products.
**Agent recommendation was:** Option C
**Student followed agent recommendation:** Yes — and added difficulty tagging, dashboard display requirement, and Week 3 labelling schedule
**Logged at:** 2026-06-26, 17:36 IST
**ADR:** ADR-008

### Decision 9: Observability and Tracing
**Options presented:** A (Langfuse only), B (Langfuse + structlog), C (OpenTelemetry)
**Student chose:** Option B. Langfuse: LLM layer (cascade spans, Mode 2 session traces, RAGAS scores attached). structlog: application layer (Celery lifecycle, ingestion steps, retrieval results, cascade decisions, cite-or-refuse events, validation failures). Five mandatory event types logged without exception.
**Student's reason:** Two layers answer different questions. The mandatory events are the ones that explain system behaviour when something goes wrong AND make the mentor review demonstrable. OpenTelemetry: correct at production scale, wrong for a single-developer 5-week project.
**Agent recommendation was:** Option B
**Student followed agent recommendation:** Yes — and specified the five mandatory event types precisely
**Logged at:** 2026-06-26, 17:39 IST
**ADR:** ADR-009

### Decision 10: Deployment Strategy
**Options presented:** A (Railway + Vercel), B (Docker Compose + Ngrok), C (Render + Vercel), D (VPS)
**Student chose:** TBD — deferred to Week 4/5 when deployment becomes immediately relevant
**Student's reason:** Not the current priority. Decision will be made when the system is ready to ship.
**Agent recommendation was:** Option B (dev) + Option A (demo deploy)
**Student followed agent recommendation:** N/A — deferred
**Logged at:** 2026-06-26, 17:42 IST
**ADR:** ADR-010 (to be written in Week 4)

## Code / Output Produced

*(links to commits or key files)*

## What the Student Built / Decided

*(filled at end of session)*

## Open Questions for Next Session

*(filled at end of session)*

## Next Session Goal

*(filled at end of session)*

---

## Summary

*(filled at end of session)*
