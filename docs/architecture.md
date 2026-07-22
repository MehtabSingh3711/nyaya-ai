# System Architecture & Technical Specification — Nyaya AI
**Project:** Nyaya AI — Indian Legal Intelligence Platform  
**Author:** Mehtab Singh  
**Version:** 1.0 Final  
**Date:** July 2026  

---

## 1. High-Level Architecture Diagram (C4 Level 2)

```
                                  +-------------------------------------------------+
                                  |         User / Web Browser (Client)             |
                                  +------------------------+------------------------+
                                                           |
                                           HTTPS / REST    |
                                                           v
                                  +------------------------+------------------------+
                                  |     Frontend Web App (Next.js 14 / React)      |
                                  |    - Dashboard & Audit History                  |
                                  |    - Contract Compliance Workstation            |
                                  |    - Legal Intelligence Chat (Mode 2)           |
                                  +------------------------+------------------------+
                                                           |
                                           HTTPS / REST    |
                                                           v
                                  +------------------------+------------------------+
                                  |       Backend API Gateway (FastAPI)             |
                                  |    - Authentication & User Sessions (JWT)       |
                                  |    - Document Ingestion & Chunker               |
                                  |    - Redis Response Caching                     |
                                  |    - Dual-Storage Contract Deletion           |
                                  +----+-------------------+-------------------+----+
                                       |                   |                   |
                     +-----------------+                   |                   +-----------------+
                     |                                     |                                     |
                     v                                     v                                     v
+--------------------+-------------------+   +-------------+--------------------+  +-----------------+------------------+
|    Remote GPU Microservice (Kaggle)    |   |    Vector Database (Qdrant)      |  |     3-Tier Cloud LLM Cascade       |
|    Exposed via Cloudflare Tunnel       |   |    - nyaya_corpus (33.6k secs)   |  |  Tier 1: Groq (Llama 3.1 8B)     |
|    - GPU 0 (cuda:0): BAAI/bge-m3       |   |    - nyaya_precedents            |  |  Tier 2: Gemini 2.0 Flash       |
|    - GPU 1 (cuda:1): bge-reranker-v2  |   |    - nyaya_contracts             |  |  Tier 3: OpenRouter Free Tier    |
+----------------------------------------+   +----------------------------------+  +------------------------------------+
```

---

## 2. Component Specifications

### A. Frontend Layer (Next.js 14)
- **Framework**: Next.js 14 (App Router), React 18, TypeScript, TailwindCSS.
- **Theme**: Premium dark mode & light mode glassmorphism design with custom CSS tokens (`--toxic-orange`, `--garnet`, `--amazon-mist`).
- **State & UI**: Real-time progress bar streaming for contract scanning, interactive Clause Navigator, themed confirmation modals (`ConfirmModal.tsx`), and floating toast notifications (`Toast.tsx`).

### B. Backend API Layer (FastAPI)
- **Framework**: FastAPI (Python 3.11+), Uvicorn.
- **Database**: SQLite (`nyaya_history.db`) with SQLAlchemy ORM for user accounts, chat sessions, message history, and contract scan records.
- **Caching**: Redis cache layer for instant retrieval of repeated legal chat queries.
- **Endpoints**:
  - `POST /api/v1/auth/register`, `POST /api/v1/auth/token`
  - `POST /api/v1/contracts/scan` (Pipelined streaming contract audit)
  - `GET /api/v1/contracts/scan/{scan_id}/export-pdf` (Report PDF generation)
  - `DELETE /api/v1/contracts/scan/{scan_id}` (Dual-storage deletion: SQLite + Qdrant Cloud)
  - `POST /api/v1/chat` (Multi-statute legal Q&A)

### C. Vector Database Layer (Qdrant)
- **Collections**:
  1. `nyaya_corpus`: 33,603 statutory sections across 1,021 Indian Acts. Hybrid vectors: 1024-dim dense (`bge-m3`) + sparse lexical weights.
  2. `nyaya_precedents`: Landmark Supreme Court / High Court case law precedents.
  3. `nyaya_contracts`: Per-contract clause vector storage for user uploads.
- **Search Strategy**: Reciprocal Rank Fusion (RRF) combining dense cosine similarity and sparse lexical matching.

### D. Remote GPU Microservice (Kaggle T4 x2)
- **Script**: `scripts/kaggle_gpu_embedding_server.py`
- **Execution**:
  - **GPU 0 (`cuda:0`)**: BAAI/bge-m3 (Dense + Sparse hybrid vector generation).
  - **GPU 1 (`cuda:1`)**: `BAAI/bge-reranker-v2-m3` (PyTorch CUDA Cross-Encoder Reranker).
- **Transport**: Automated Cloudflare Tunnel (`cloudflared`) exposing FastAPI endpoints to the local backend.
- **Fallback**: Local CPU ONNX (`jinaai/jina-reranker-v1-turbo-en`) if remote URL is unconfigured.

### E. LLM Cascade Layer
- **Tier 1**: Groq (`llama-3.1-8b-instant`) — ~1.8s response time.
- **Tier 2**: Gemini (`gemini-2.0-flash`) via OpenAI-compatible endpoint.
- **Tier 3**: OpenRouter (`nvidia/nemotron-3-ultra-550b-a55b:free` or Qwen).
- **Schema Enforcement**: Pydantic v2 `CitedAnswer` and `RiskAssessment` schemas with strict `can_answer` and `confidence` checks.

---

## 3. Data Flow Pipelines

### Pipeline 1: Contract Compliance Scanning (Mode 1)
```
[User Uploads PDF] 
    ---> PyMuPDF Text Extraction 
    ---> Structural Chunker (Regex Section Boundaries) 
    ---> Query Expansion (expand_legal_query) 
    ---> BGE-M3 Hybrid Embeddings (GPU 0) 
    ---> Qdrant Hybrid Search (Top 100 Candidates) 
    ---> BGE-Reranker v2-m3 Reranking (GPU 1, Top 5 Chunks) 
    ---> Precedent Search (nyaya_precedents) 
    ---> 3-Tier LLM Cascade Risk Analysis 
    ---> Verbatim Grounding Verification (verify_grounding) 
    ---> Real-time Stream to Next.js UI
```

### Pipeline 2: Legal Intelligence Chat (Mode 2)
```
[User Asks Legal Question] 
    ---> Redis Cache Check (Return if HIT) 
    ---> Legal Query Expansion (expand_legal_query) 
    ---> BGE-M3 Hybrid Embeddings (GPU 0) 
    ---> Qdrant Hybrid Search 
    ---> Cross-Encoder Rerank (GPU 1) 
    ---> 3-Tier LLM Cascade (JSON Mode) 
    ---> Pydantic Validation & Grounding Check 
    ---> Save to SQLite & Redis Cache 
    ---> Render Response + Citations + Quotes in UI
```
