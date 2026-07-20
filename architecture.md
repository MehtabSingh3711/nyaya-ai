# Architecture — Nyaya AI: Contract Intelligence

**Project:** Nyaya AI — Indian Legal Intelligence Platform
**Module:** Contract Intelligence (Internship Scope)
**Author:** Mehtab Singh
**Date:** 20 July 2026
**Status:** Approved — all decisions logged in ADR-001 through ADR-012 (Amended)
**Timeline:** Extended to 25 July 2026

---

## 1. System Overview

Nyaya AI is a two-mode legal intelligence platform. Both modes retrieve from the same underlying infrastructure — a shared Indian legal corpus and a per-session contract index. The retrieval, cascade, and citation logic are shared components; what differs between modes is the trigger (automatic scan vs. conversational query) and the output shape (structured risk report vs. cited chat response).

```
                        ┌──────────────────────────────────┐
                        │         Nyaya AI Platform         │
                        │                                   │
              ┌─────────┤  Mode 1: Automatic Scan           │
              │         │  Mode 2: Legal Intelligence Chat  │
              │         └──────────────────────────────────┘
              │
   ┌──────────▼──────────────────────────────────────────────────┐
   │                   Shared Infrastructure                      │
   │                                                              │
   │   ┌─────────────────┐ ┌──────────────────┐ ┌──────────────┐ │
   │   │  nyaya_corpus   │ │nyaya_precedents  │ │nyaya_contract│ │
   │   │  (Qdrant Cloud) │ │(Qdrant Cloud)    │ │(Qdrant Cloud)│ │
   │   │  ICA, MSME,     │ │SC Case-Law       │ │User-uploaded │ │
   │   │  DPDP, Mediation│ │Precedents        │ │Contracts     │ │
   │   └─────────────────┘ └──────────────────┘ └──────────────┘ │
   │                                                             │
   │   BGE-M3 (dense) + Lexical Weights (sparse) + Jina Reranker │
   │   Hybrid retrieval: single Qdrant named-vector query         │
   │                                                             │
   │   LLM Cascade: Groq (Llama 3.1 8B) ──► Gemini Cloud ──► OR  │
   │   (all free — Tier 1 via Groq, Tier 2 via Gemini Cloud)     │
   └─────────────────────────────────────────────────────────────┘
```

---

## 2. Full System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Next.js Frontend                            │
│  ┌──────────────────────┐  ┌──────────────────────────────────────┐ │
│  │     Scan Panel        │  │         Chat Panel                   │ │
│  │  Drag-drop upload     │  │  Interactive conversations           │ │
│  │  Risk flags (R/Y/G)   │  │  Citation sidebar                    │ │
│  │  Report PDF export    │  │  "Insufficient Info" refusal state   │ │
│  └──────────┬────────────┘  └────────────────┬─────────────────────┘ │
└─────────────┼──────────────────────────────────┼─────────────────────┘
              │ POST /api/v1/contracts/scan      │ POST /api/v1/chat
              │ GET  /api/v1/contracts/scan/{id} │ GET  /api/v1/chat/sessions
              ▼                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        FastAPI Backend                              │
│                                                                     │
│   POST /scan ──► validate ──► write file ──► trigger BackgroundTask │
│   GET  /scan/{id} ──► query SQLite ──► return complete scan results │
│   POST /chat ──► retrieve ──► cascade ──► save message to SQLite    │
│   GET  /health ──► verify SQLite connectivity                       │
└──────────────────┬──────────────────────────────────────────────────┘
                   │
         ┌─────────┴──────────┐
         │                    │
         ▼                    ▼
┌─────────────────┐  ┌──────────────────────────────────────────────┐
│  SQLite DB      │  │        BackgroundTasks Thread Pool           │
│                 │  │                                              │
│  • scans table  │  │  run_contract_scan_task(scan_id, file_path)  │
│    (history)    │  │  ┌────────────────────────────────────────┐  │
│                 │  │  │ 1. Parse PDF/DOCX (PyMuPDF)            │  │
│  • sessions     │  │  │ 2. Clause chunking                     │  │
│    table (chat) │  │  │ 3. Embed chunks (BGE-M3 FastEmbed)     │  │
│                 │  │  │ 4. Run risk scan engines (ICA/MSME/Act)│  │
│  • messages     │  │  │ 5. Validate outputs (Pydantic v2)      │  │
│    table        │  │  │ 6. Store scan JSON in SQLite           │  │
│                 │  │  └────────────────────────────────────────┘  │
└─────────────────┘  └──────────────────────────────────────────────┘
                                        │
                           ┌────────────┴───────────────┐
                           │                            │
                           ▼                            ▼
              ┌─────────────────────┐    ┌──────────────────────────┐
              │  Qdrant Cloud       │    │  Cloud API LLM Cascade   │
              │                     │    │                          │
              │  • nyaya_corpus     │    │  Tier 1: Groq Llama 3.1  │
              │  • nyaya_precedents │    │  Tier 2: Gemini Cloud    │
              │  • nyaya_contracts  │    │  Tier 3: OpenRouter      │
              │                     │    └──────────────────────────┘
              │  Named vectors:     │
              │  dense (BGE-M3)     │
              │  sparse (lexical)   │
              │                     │
              │  Hybrid retrieval   │
              │  + Jina Reranker    │
              └─────────────────────┘
```

---

## 3. Document Ingestion Pipeline (Mode 1)

**ADR-001:** Structural chunking primary; LLM-based structural chunking as fallback.

```
Input: PDF / DOCX
       │
       ▼
  Format detection
       │
  ┌────┴───────────────────────────┐
  │ DOCX           │ Native PDF    │
  ▼                ▼               │
docx-parser      PyMuPDF           │
  └────────────────┬───────────────┘
                   ▼
          Structural chunking
          (detect clause headings,
           numbered sections)
                   │
           ┌───────┴──────────────┐
           │ Structure detected?  │
           └───────┬──────────────┘
            Yes    │    No
            │      │    └──→ Regex/heuristic fallback
            ▼      ▼
      Clause-level chunks with metadata:
      { clause_number, clause_heading, page, text }
                   │
                   ▼
       Embed: BGE-M3 (dense + sparse)
                   │
                   ▼
       Index → nyaya_contracts (Qdrant)
```

---

## 4. Indian Legal Corpus & Precedents

**ADR-003:** `nyaya_corpus` — persistent, versioned, shared across all users.

### Ingestion timeline:
* **Week 1-2**: Indian Contract Act 1872, MSME Development Act 2006, IT Act 2000, IPC, CPC.
* **Week 3**: DPDP Act 2023, Mediation Act 2023, Telecommunications Act 2023, Jan Vishwas Act 2023.
* **Week 4 (Current)**: Ingestion of `nyaya_precedents` (Supreme Court landmark rulings) into Qdrant Cloud.

---

## 5. Retrieval Pipeline

**ADR-002 (BGE-M3 + Jina Reranker), ADR-003 (named vectors, hybrid search)**

```
Query (question or scan trigger)
       │
       ▼
Determine collection scope:
  Mode 2 general question → nyaya_corpus + nyaya_precedents
  Mode 2 document question → nyaya_corpus + nyaya_precedents + nyaya_contracts
  Mode 1 scan → nyaya_contracts (risk engines query corpus separately)
       │
       ▼
Hybrid retrieval (single Qdrant named-vector query per collection):
  dense: BGE-M3 cosine similarity
  sparse: lexical token weights
  Qdrant fusion → top-k candidates
       │
       ▼
Jina Reranker v1 Turbo
  Reads (query, chunk) pair jointly
  Re-scores top-k → re-sorted final candidates (top-5)
       │
       ▼
Top-5 chunks passed to LLM cascade
```

---

## 6. LLM Cascade

**ADR-004:** Confidence-threshold cascade, fully free.

```
Query + retrieved context (top-5 chunks)
       │
       ▼
┌──────────────────────────────────────┐
│  Tier 1: Groq (Llama 3.1 8B)         │
│  Fast, Cloud API, 2s response time   │
│  Returns: structured output + conf.  │
└──────────────────┬───────────────────┘
                   │
          confidence ≥ 0.70?
          Pydantic valid?
                   │
             Yes   │   No (either)
              │    │
              │    ▼
              │  ┌──────────────────────────────────────┐
              │  │  Tier 2: Gemini Cloud (2.5 Flash Lite)│
              │  │  Excellent reasoning, cloud, free API│
              │  │  Returns: structured output + conf.  │
              │  └──────────────────┬───────────────────┘
              │                     │
              │            confidence ≥ 0.70?
              │            Pydantic valid?
              │                     │
              │               Yes   │   No (either)
              │                │    │
              │                │    ▼
              │                │  ┌──────────────────────────────────────┐
              │                │  │  Tier 3: OpenRouter (Qwen 3 Free)   │
              │                │  │  Online fallback, last resort        │
              │                │  │  Returns: structured output + conf.  │
              │                │  └──────────────────┬───────────────────┘
              │                │                     │
              │                │            confidence ≥ 0.70?
              │                │            Pydantic valid?
              │                │                     │
              │                │               Yes   │   No
              │                │                │    ▼
              │                │                │  Cite-or-refuse:
              │                │                │  { can_answer: false,
              │                │                │    reason: "...",
              │                │                │    confidence: 0.XX }
              └────────────────┘────────────────┘
                       Return to caller
```

---

## 7. Tech Stack — Confirmed Decisions

| Component | Choice | ADR |
|-----------|--------|-----|
| Document parsing | PyMuPDF + docx-parser | — |
| Chunking | Structural → Heuristic fallback | ADR-001 |
| Embeddings | BGE-M3 via Qdrant FastEmbed | ADR-002 |
| Reranking | Jina Reranker v1 Turbo | ADR-002 |
| Vector DB | Qdrant Cloud — 3 collections, named vectors | ADR-003 |
| LLM Tier 1 | Groq (Llama 3.1 8B Instant) | ADR-004 |
| LLM Tier 2 | Gemini (2.5 Flash Lite via OpenAI Endpoint) | ADR-004 |
| LLM Tier 3 | OpenRouter (Qwen 3 Free) | ADR-004 |
| Extraction | Pydantic v2 + JSON mode | ADR-005 |
| Backend | FastAPI + BackgroundTasks + SQLite | ADR-006 |
| Frontend | Next.js + shadcn/ui (dark navy) | ADR-007 |
| Evaluation | RAGAS + custom citation metric | ADR-008 |
| PDF Export | ReportLab PDF Exporter | — |

---

## 8. Build Order and Weekly Milestones

* **Week 1**: Ingested statutory corpus (ICA, MSME, IT, IPC, CPC). Dense retrieval index and RAG CLI. *(Completed)*
* **Week 2**: Contract parser chunker, MSME & ICA §27 scan engines, and Cloud LLM Cascade. *(Completed)*
* **Week 3**: Ingested new laws (DPDP, Mediation, Telecom, Jan Vishwas). Setup FastAPI backend, SQLite history database, and ReportLab PDF exporter. *(Completed)*
* **Week 4 (Current)**: Ingest case precedents dataset (`nyaya_precedents`) into Qdrant Cloud. Build Next.js frontend pages.
* **Week 5**: Polish, final evaluations, Loom walkthrough, and presentation delivery (Due July 25).
