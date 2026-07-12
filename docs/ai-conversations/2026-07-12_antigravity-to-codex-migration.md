# AI Session Log — 2026-07-12 — Antigravity to Codex Migration

**Agent:** Antigravity (Gemini) — FINAL SESSION
**Phase:** Week 2 → Week 3 handoff
**Session opened:** 2026-07-12T11:51 IST

---

## Session Goal

Prepare a zero-information-loss handoff from Antigravity (Gemini) to ChatGPT Codex. Update all project documentation so Codex has full context on day one.

---

## What Was Built in Weeks 0–2 (Antigravity Sessions)

### Week 0 — Foundation (June 22–28)

| Deliverable | File(s) | Session Log |
|---|---|---|
| Problem Statement | `problem-statement.md` | `2026-06-23_problem-definition-design-docs.md` |
| Initial Design Doc | `initial-design-doc.md` | `2026-06-23_problem-definition-design-docs.md` |
| Architecture Document | `architecture.md` | `2026-06-25_architecture-decisions.md` |
| ADRs 001–009 | `docs/adr/ADR-001` through `ADR-009` | `2026-06-25_architecture-decisions.md` |
| README + Diagrams | `README.md` | `2026-06-26_readme-and-diagrams.md` |
| Project scaffolding | `pyproject.toml`, `requirements.txt`, `.gitignore`, `docker-compose.yml` | Various |

### Week 1 — Core Build (June 30 – July 5)

| Layer | Component | File(s) | Tests |
|---|---|---|---|
| Config & Schemas | Centralized config, Pydantic v2 models | `nyaya_ai/config.py`, `nyaya_ai/schemas.py` | 22 (test_schemas.py) |
| Ingestion — Chunker | Regex section boundary detection, sub-section splitting | `nyaya_ai/ingest/chunker.py` | 10 (test_chunker.py) |
| Ingestion — Dedup | Normalized (act, section) cross-dataset dedup | `nyaya_ai/ingest/dedup.py` | 10 (test_dedup.py) |
| Ingestion — Loaders | HuggingFace dataset loaders (3 datasets) | `nyaya_ai/ingest/loaders.py` | — |
| Retrieval — Embedder | BGE-M3 wrapper (embed_documents, embed_query) | `nyaya_ai/retrieval/embedder.py` | 8 (test_embedder.py) |
| Storage — Qdrant | Singleton client, create/upsert/search/count | `nyaya_ai/store/qdrant.py` | 13 (test_qdrant.py) |
| LLM — Prompts | System prompt with CitedAnswer schema | `nyaya_ai/llm/prompts.py` | — |
| LLM — Cascade (v1) | Ollama Tier 1 only (Phi-3 Mini) | `nyaya_ai/llm/cascade.py` (v1) | 20 (test_cascade.py) |
| CLI — Ingest | Full ingestion pipeline script | `ingest.py` | — |
| CLI — Query | REPL with rich display | `query.py` | — |

### Week 2 — Cascade Replacement + Stabilization (July 7–12)

| Change | Reason |
|---|---|
| Replaced Ollama/Phi-3 with Groq (Llama 3.1 8B) Tier 1 | ~5 min/query latency on local CPU was unusable |
| Added Gemini 2.5 Flash Lite as Tier 2 | OpenAI-compatible endpoint, zero new dependencies |
| Added OpenRouter (Qwen 3 Next 80B free) as Tier 3 | Free-tier fallback |
| Added `_extract_json()` robust parser | Small LLMs wrap JSON in markdown fences |
| Fixed mock-compatibility bug in cascade tests | `_TIERS` module-level list captured function refs at import time, breaking `mock.patch` |
| Added `.env` support via `python-dotenv` | API keys no longer require `$env:` export every session |
| Colab GPU embedding workflow | BGE-M3 embedding of 33,603 sections done on T4 GPU |

---

## Key Decisions Made (Summary)

| Decision | Options Considered | Student Chose | Logged In |
|---|---|---|---|
| Chunking strategy | Semantic / Structural / LLM-assisted | Structural (regex) | ADR-001 |
| Embedding model | BGE-M3 / E5 / OpenAI | BGE-M3 | ADR-002 |
| Vector DB | Qdrant / Chroma / Pinecone | Qdrant | ADR-003 |
| LLM cascade design | Fixed / Confidence cascade / Hybrid / Router | Confidence cascade (Option B) | ADR-004 |
| Cascade replacement | Stay local / Cloud APIs / Hybrid | Cloud APIs (Groq/Gemini/OpenRouter) | ADR-004 Amendment (STATUS section) |
| Qdrant storage mode | Docker / Cloud / Local file-based | Local file-based (Option C) | Session log 2026-06-30 |
| geekyrakshit dataset | Keep / Drop | Drop (mratanusarkar alone is sufficient) | Session log |

---

## Colab GPU Embedding Workflow

The BGE-M3 embedding of 33,603 sections was done on Google Colab with a T4 GPU:

1. **Problem:** BGE-M3 + local Ollama LLM consumed all ~3.4 GB available RAM. Embedding 33,603 sections on CPU would take ~9 hours.
2. **Solution:** Uploaded the ingestion pipeline to Google Colab.
3. **Key fix:** Batch size reduced from default to **8** to avoid CUDA OOM on T4 GPU (16 GB VRAM).
4. **Result:** Full embedding completed in ~25 minutes.
5. **Export:** Qdrant snapshot exported from Colab, downloaded, and imported into local `./qdrant_data` directory.
6. **Verification:** `get_point_count()` returns 33,603. `search()` returns relevant results.

---

## Current Test Suite

```
88 tests, all passing (as of 2026-07-12)

tests/test_schemas.py     — 22 tests (Citation, CitedAnswer, CorpusChunk validation)
tests/test_chunker.py     — 10 tests (pre-sectioned, raw text, long sections, chapters)
tests/test_dedup.py       — 10 tests (duplicate detection, normalization)
tests/test_embedder.py    —  8 tests (embed_documents, embed_query, batch consistency)
tests/test_qdrant.py      — 13 tests (create, upsert, search, point count — all mocked)
tests/test_cascade.py     — 20 tests (3-tier escalation, retry, fallback, JSON extraction)
tests/debug_regex.py      —  (utility, not a test file)
tests/datacheck.py        —  (utility, not a test file)
```

Run with: `pytest tests/ -v`

---

## Repository State

- **Branch:** `main`
- **Last commit:** `e0c12f3` — "Stage 1 Completed: CLI" (pushed 2026-07-12)
- **Remote:** `https://github.com/MehtabSingh3711/nyaya-ai.git`
- **Qdrant data:** `./qdrant_data/` directory (gitignored, ~600 MB). Must be regenerated via `python ingest.py` or by importing the Colab snapshot if lost.
- **API keys:** In `.env` file (gitignored). Keys needed: `GROQ_API_KEY`, `GEMINI_API_KEY`, `OPENROUTER_API_KEY`.

---

## File Structure (complete)

```
nyaya-ai/
├── AGENTS.md                      # Agent system prompt (updated with STATUS section)
├── README.md
├── architecture.md
├── problem-statement.md
├── initial-design-doc.md
├── pyproject.toml
├── requirements.txt
├── docker-compose.yml
├── .env                           # API keys (gitignored)
├── .gitignore
├── ingest.py                      # CLI: full ingestion pipeline
├── query.py                       # CLI: Mode 2 REPL
├── datacheck.py                   # Utility: dataset stats
├── codebase_audit.md              # Full codebase audit (2026-07-09)
├── docs/
│   ├── adr/
│   │   ├── ADR-001-chunking-strategy.md
│   │   ├── ADR-002-embedding-model.md
│   │   ├── ADR-003-vector-db-architecture.md
│   │   ├── ADR-004-llm-cascade.md
│   │   ├── ADR-005-extraction-framework.md
│   │   ├── ADR-006-backend-framework.md
│   │   ├── ADR-007-frontend.md
│   │   ├── ADR-008-evaluation-framework.md
│   │   └── ADR-009-observability.md
│   └── ai-conversations/
│       ├── 2026-06-23_problem-definition-design-docs.md
│       ├── 2026-06-25_architecture-decisions.md
│       ├── 2026-06-26_readme-and-diagrams.md
│       ├── 2026-06-30_cli-core-build.md
│       └── 2026-07-12_antigravity-to-codex-migration.md  ← THIS FILE
├── nyaya_ai/
│   ├── __init__.py
│   ├── config.py                  # All constants + API keys from .env
│   ├── schemas.py                 # Citation, CitedAnswer, CorpusChunk
│   ├── ingest/
│   │   ├── __init__.py
│   │   ├── chunker.py             # Regex section splitter
│   │   ├── dedup.py               # DedupRegistry
│   │   └── loaders.py             # HF dataset loaders
│   ├── retrieval/
│   │   ├── __init__.py
│   │   └── embedder.py            # BGE-M3 wrapper
│   ├── store/
│   │   ├── __init__.py
│   │   └── qdrant.py              # Qdrant client (singleton, local file mode)
│   └── llm/
│       ├── __init__.py
│       ├── prompts.py             # System prompt builder
│       └── cascade.py             # 3-tier cloud cascade (Groq → Gemini → OpenRouter)
├── tests/
│   ├── test_schemas.py            # 22 tests
│   ├── test_chunker.py            # 10 tests
│   ├── test_dedup.py              # 10 tests
│   ├── test_embedder.py           #  8 tests
│   ├── test_qdrant.py             # 13 tests
│   ├── test_cascade.py            # 20 tests (+ 5 extract_json)
│   └── debug_regex.py             # One-off regex debug utility
└── qdrant_data/                   # Qdrant local storage (gitignored, ~600 MB)
```

---

## Handoff Note

**Development continues in ChatGPT Codex starting 2026-07-12.**

See `AGENTS.md` STATUS section for the current state of what is built, what is not, and what architectural decisions are pending.

All rules in `AGENTS.md` (decision protocol, session logging, spec-before-code, cite-or-refuse) apply identically to Codex. The student owns every decision. The agent surfaces options.

This is the final Antigravity (Gemini) session log.
