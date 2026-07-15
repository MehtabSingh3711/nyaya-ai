# ADR-010 — Deployment: Consolidated HuggingFace Docker Space

**Date:** 2026-07-15
**Status:** Accepted
**Author:** Mehtab Singh
**Decider:** Mehtab Singh
**Depends on:** ADR-006 (backend framework), ADR-002 (embedding model), ADR-003 (vector DB)

---

## Context

The original architecture assumed Railway (backend) + Vercel (frontend) + local Qdrant. Week 4 deployment planning revealed:

1. **Three separate platforms** (Railway + Vercel + local Qdrant) creates operational complexity for a solo 5-week build — three deploy targets, three billing accounts, three sets of environment variables.
2. **The heaviest dependency is the ML models** (BGE-M3 at ~1.1 GB + bge-reranker-v2-m3 at ~1.1 GB in FP16), not the API layer. Railway's free tier (512 MB RAM) cannot host these models in-process.
3. **HuggingFace Spaces is purpose-built for ML model serving** — the free CPU tier provides 16 GB RAM and 2 vCPUs, enough to load both models (~4 GB combined with overhead) alongside FastAPI + Celery + Redis.

The decision was made to consolidate the entire backend onto HuggingFace Spaces (Docker SDK) and move Qdrant to Qdrant Cloud as the only external managed service.

---

## Decision

**Host the entire backend in a single HuggingFace Docker Space:**
- FastAPI web server (port 7860)
- Celery worker (background task processing)
- Redis server (Celery broker + session store)
- BGE-M3 embedding model (FP16, loaded on startup)
- bge-reranker-v2-m3 cross-encoder (FP16, loaded on startup)

**Qdrant Cloud** as the sole external managed service:
- Free tier: 0.5 vCPU, 1 GB RAM, 4 GB disk
- Hosts `nyaya_corpus` collection (~33,603 points, 1024d dense + sparse)
- Connected via QDRANT_URL + QDRANT_API_KEY environment variables

**Frontend** (Next.js, per ADR-007) deployed on Vercel free tier — this is a static/SSR frontend, not a heavyweight service, so Vercel remains the right host.

---

## Feasibility Verification

### Q1: Can HF Docker Space run multiple processes?

**Yes.** HuggingFace Docker Spaces run a single container, but `supervisord` inside the container is a well-documented, widely-used pattern for running multiple processes. The Dockerfile uses `supervisord` as the entrypoint to manage:

```ini
[supervisord]
nodaemon=true

[program:redis]
command=redis-server --maxmemory 512mb --maxmemory-policy allkeys-lru
autostart=true
autorestart=true

[program:celery]
command=celery -A nyaya_ai.tasks worker --loglevel=info --concurrency=1
autostart=true
autorestart=true

[program:fastapi]
command=uvicorn nyaya_ai.api.main:app --host 0.0.0.0 --port 7860
autostart=true
autorestart=true
```

Port 7860 is HF Spaces' required application port. Only `/tmp` is reliably writable — Redis must be configured to use `/tmp` for AOF/RDB persistence (or run memory-only, which is acceptable since Redis data is ephemeral session state).

### Q2: HF Spaces Free Tier Specs

| Resource | Free CPU Tier |
|---|---|
| vCPU | 2 |
| RAM | 16 GB |
| Disk | 50 GB (non-persistent) |
| Sleep on inactivity | After 48 hours |
| GPU | None (ZeroGPU available separately) |

**Inactivity impact:** After 48h without requests, the Space sleeps. On next request, it cold-starts (rebuilds the container). This means:
- Redis data is lost → session state must be re-initialized (acceptable — sessions are short-lived)
- Models are re-loaded from HuggingFace cache → ~30-60 second cold start
- Qdrant Cloud data is unaffected (external service)

For the internship demo phase, this is acceptable. A keep-alive ping (GitHub Action every 12h) can prevent sleeping if needed.

### Q3: Memory Budget

| Component | RAM (approx) |
|---|---|
| BGE-M3 (FP16) | ~1.1 GB |
| bge-reranker-v2-m3 (FP16) | ~1.1 GB |
| Redis (capped) | 0.5 GB |
| FastAPI + Celery | ~0.3 GB |
| Python + OS overhead | ~1.0 GB |
| **Total** | **~4.0 GB** |
| **HF Free Tier RAM** | **16 GB** |
| **Headroom** | **~12 GB** |

**Verdict: Fits comfortably.** 4 GB of 16 GB used, leaving 12 GB headroom for peak inference memory (batch tokenization spikes, concurrent requests).

---

## Reasoning: Why HF Spaces over Railway

| Factor | HF Spaces | Railway |
|---|---|---|
| **Free tier RAM** | 16 GB | 512 MB |
| **ML model hosting** | Native strength — purpose-built | Not designed for it — models OOM |
| **BGE-M3 + reranker** | Loads comfortably | Cannot fit in 512 MB |
| **Multi-process** | supervisord pattern | Native (but RAM-limited) |
| **Sleep timer** | 48h inactivity | Similar (free tier limitations) |
| **Disk** | 50 GB | Limited on free tier |

The key insight: **the heaviest dependency is the ML models, not the API layer.** Hosting the models and the API in the same process avoids internal network hops for embedding/reranking, which are called on every query.

---

## Architecture After This Decision

```
┌─────────────────────────────────────────────┐
│         HuggingFace Docker Space            │
│         (Free CPU Tier: 16GB RAM)           │
│                                             │
│  ┌──────────┐  ┌───────┐  ┌────────────┐   │
│  │ FastAPI   │  │ Redis │  │ Celery     │   │
│  │ :7860     │  │ :6379 │  │ worker     │   │
│  └────┬─────┘  └───┬───┘  └──────┬─────┘   │
│       │            │             │           │
│  ┌────▼────────────▼─────────────▼────────┐ │
│  │  In-process Python modules             │ │
│  │  • BGE-M3 (1.1 GB FP16)               │ │
│  │  • bge-reranker-v2-m3 (1.1 GB FP16)   │ │
│  │  • LLM cascade (API calls to Groq/    │ │
│  │    Gemini/OpenRouter — no local LLM)   │ │
│  └────────────────────────────────────────┘ │
└─────────────────────┬───────────────────────┘
                      │ HTTPS
           ┌──────────▼──────────┐
           │   Qdrant Cloud      │
           │   (Free Tier)       │
           │   nyaya_corpus      │
           │   33,603 points     │
           └─────────────────────┘
```

Frontend (Next.js on Vercel) calls the HF Space API at `https://<space>.hf.space`.

---

## Configuration Changes Required

```python
# config.py — updated for cloud deployment
QDRANT_URL = os.getenv("QDRANT_URL")      # Qdrant Cloud endpoint
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")  # Qdrant Cloud API key
```

The existing `QDRANT_PATH` (local file mode) remains as the development default. `QDRANT_URL` takes precedence when set.

---

## Cold Start Strategy

On sleep → wake:
1. Container rebuilds from Docker image (cached on HF infrastructure)
2. Redis starts fresh — no stale sessions, Celery queue empty (correct behavior)
3. BGE-M3 + reranker loaded from HuggingFace model cache (~30-60s)
4. First request after cold start is slow; subsequent requests are normal

For the demo: trigger a warm-up request before the presentation.

---

## Consequences

**Positive:**
- Single deploy target for all backend logic — one `git push` deploys everything
- 16 GB RAM — no model OOM concerns
- HF model caching — BGE-M3 and reranker download once, cached across restarts
- No Railway billing or account needed
- Qdrant Cloud is the only external dependency, and it's managed/reliable

**Negative / Watch:**
- 48h sleep timer on free tier — may need keep-alive for persistent availability
- Cold start ~30-60s — not instant, but acceptable for demo/interview usage patterns
- Redis data ephemeral — session history lost on restart (by design — sessions are short-lived)
- Single container = single point of failure (acceptable for internship scope)

---

## Alternatives Rejected

- **Railway (backend) + Vercel (frontend) + local Qdrant:** Original plan. Railway's 512 MB RAM cannot host ML models. Three platforms = too much operational overhead for one person.
- **Railway (API) + HF Space (models only):** Split architecture where Railway calls a separate HF Space for embedding/reranking. Adds internal network latency (~200ms per call) and doubles deployment complexity.
- **Jina AI Embedding API:** Cannot produce sparse vectors (lexical weights). Switching from BGE-M3 would destroy the hybrid retrieval pipeline built in ADR-011. Non-starter.
