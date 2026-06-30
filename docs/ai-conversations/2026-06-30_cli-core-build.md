# AI Session Log — 2026-06-30 — CLI-First Core Build (ingest.py + query.py)
**Agent:** Antigravity (Claude Opus 4.6 — Thinking)
**Phase:** Week 2 — Core
**Session opened:** 15:32 IST

## Session Goal
Build CLI-first: a single `ingest.py` script and a single `query.py` script. No FastAPI, Celery, Redis, or frontend — those come after the core retrieval loop is proven. Follow `/spec` before writing either.

## Scope Clarifications (pre-spec)

1. **Mode 2 first, not Mode 1.** Build the legal intelligence chat against the statutory corpus first. User contract upload comes later once retrieval is proven on clean statutory text.
2. **Corpus source: both.** HuggingFace datasets from Layer1-IndianLaw.txt AND Constitution.pdf. HF datasets need dedup filtering to avoid repetitions across overlapping datasets.
3. **query.py is REPL mode.** Interactive `nyaya>` prompt, not single-shot.
4. **Ollama installed, Qdrant not.** Spec must include Qdrant Docker setup.

## Decisions Log

### Spec Clarification: BGE-M3 Cache
**Student chose:** Default HuggingFace cache, no custom path
**Logged at:** 2026-06-30, 16:07 IST

### Spec Clarification: Ollama Model Tag
**Student chose:** `phi3:3.8b` — confirmed pulled and available
**Logged at:** 2026-06-30, 16:07 IST

### Spec Clarification: Constitution.pdf Scope
**Student chose:** Defer to second pass. First ingestion covers only HF datasets.
**Student's reason:** Out of locked Week 1 scope. Core query loop must be proven on statutory corpus first.
**Logged at:** 2026-06-30, 16:07 IST

## Summary
[fill in at end of session]
