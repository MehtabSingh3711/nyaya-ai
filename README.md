# Nyaya AI — Indian Legal Intelligence Platform

> *Know what you sign.*

![Status](https://img.shields.io/badge/status-active%20development-green)
![Segment](https://img.shields.io/badge/segment-3%20%E2%80%94%20Applied%20AI-blue)
![Problem](https://img.shields.io/badge/problem-C1%20Contract%20Intelligence-purple)
![Tests](https://img.shields.io/badge/tests-160%20passing-success)

Nyaya (न्याय) is a production-grade Indian Legal Intelligence Platform designed to analyze contracts, verify compliance, and answer legal queries with high-precision citations of Indian statutory law.

---

## 🚀 Current Status & Achievements (Week 3)

We have built a fully functional CLI pipeline for ingestion and retrieval with a robust evaluation harness. Here is what is working:

1. **Statutory Corpus Ingested & Indexed (Qdrant Cloud)**:
   * **Historical Central Acts**: 33,603 sections across 1,021 Acts (source: `mratanusarkar/Indian-Laws`).
   * **2023 Criminal Justice Reforms**: 1,059 sections across **BNS, BNSS, and BSA** (source: `GSMS-B`).
   * **Post-2021 Business/Data Laws**: Verbatim sections of **DPDP Act 2023**, **Mediation Act 2023**, **Telecommunications Act 2023**, and the **Jan Vishwas Act 2023**.
2. **Hybrid Retrieval (Dense + Sparse)**:
   * **Dense**: BGE-M3 (1024-dim, Cosine) on GPU.
   * **Sparse**: BGE-M3 lexical token weights (Qdrant named sparse vectors).
   * Combined using RRF (Reciprocal Rank Fusion) and gated via a Jina Reranker relevance gate.
3. **Cloud LLM Cascade (₹0 Cost / Instant Latency)**:
   * **Tier 1**: Groq (Llama 3.1 8B Instant) — ~2s response time.
   * **Tier 2**: Gemini (2.5 Flash Lite via OpenAI-compatible endpoint).
   * **Tier 3**: OpenRouter (Qwen 3 Next 80B Free).
4. **Heuristic Contract Chunker**:
   * Scans uploaded agreements line-by-line, splitting clauses using section symbols (`§`), numbered headers (`Section`, `Clause`, `Article`), and standalone capital legal titles.
5. **Quality Assurance**:
   * Over **160 unit and integration tests passing** covering schemas, chunking, embedding, deduplication, Qdrant store, and cascade execution.

---

## 🛠️ Core Tech Stack

| Layer | Technology |
|---|---|
| **Document Parsing** | PyMuPDF (native PDF text extractor) |
| **Embeddings** | BAAI/bge-m3 (dense + sparse hybrid) |
| **Vector DB** | Qdrant Cloud (Managed, named vectors) |
| **Reranker** | Jina Reranker v1 Turbo (`CONTRACT_RELEVANCE_THRESHOLD = -0.80`) |
| **LLMs** | Llama 3.1 8B (Groq) · Gemini 2.5 Flash Lite · Qwen 3 (OpenRouter) |
| **Validation** | Pydantic v2 (Strict `CitedAnswer` and `CorpusChunk` validation) |
| **Tests** | pytest |

---

## 📁 Repository Structure

```
├── nyaya_ai/               # Core packages
│   ├── contracts/          # Mode 1: Contract Analysis (chunker, scanner, extractor)
│   ├── ingest/             # Ingestion pipelines (loaders, deduplication, chunker)
│   ├── retrieval/          # RAG search (embedder, relevance gate, cascade)
│   ├── store/              # Qdrant client, upserts, and search queries
│   ├── config.py           # Global settings, model configs, and env loading
│   └── schemas.py          # Pydantic v2 schema definitions (CitedAnswer, CorpusChunk)
├── new_laws/               # Custom statutory JSON files and Colab scripts
├── tests/                  # Complete test suite (160+ passing tests)
├── ingest.py               # statutory ingestion script CLI
├── ingest_custom.py        # Ingests a custom structured JSON bare act
└── query.py                # Mode 2: Legal Intelligence RAG Chat CLI
```

---

## ⚙️ Quickstart (CLI)

### 1. Prerequisites
Install dependencies:
```bash
pip install -r requirements.txt
```

### 2. Environment Setup (`.env`)
Create a `.env` file in the root directory:
```env
GROQ_API_KEY=your_groq_key
GEMINI_API_KEY=your_gemini_key
OPENROUTER_API_KEY=your_openrouter_key
QDRANT_URL=https://your-qdrant-cloud-cluster.aws.cloud.qdrant.io
QDRANT_API_KEY=your_qdrant_api_key
HF_TOKEN=your_huggingface_read_token
```

### 3. Run Ingestion (Optional - data is already in Qdrant Cloud)
To ingest only new reform acts locally:
```bash
python ingest.py --reforms-only
```
To ingest a custom bare act:
```bash
python ingest_custom.py new_laws/dpdp_act.json
```

### 4. Run RAG Query (Mode 2)
```bash
python query.py "What are the rules for transferring data outside India under DPDP Act 2023?"
```

---

## ⚡ FastAPI Backend API Specifications

The FastAPI backend is fully implemented and connects to our core retrieval and scanning models. 

### 1. How to run the API locally
```bash
uvicorn nyaya_ai.api.main:app --reload
```
The server will start at `http://127.0.0.1:8000` and automatically create the SQLite database file `nyaya_history.db` in your root directory.

### 2. Available API Endpoints

#### RAG Chat (Mode 2) & History
* **`POST /api/v1/chat`**: Performs hybrid search, rerank, and cascade reasoning on the user message. Returns `{ "session_id": str, "answer": CitedAnswer }`.
* **`GET /api/v1/chat/sessions`**: Returns a list of all historical chat session metadata for the "Resume Chat" sidebar.
* **`GET /api/v1/chat/sessions/{session_id}`**: Retrieves the full chronological message log of a chat session, including user inputs, assistant responses, and parsed citations.
* **`DELETE /api/v1/chat/sessions/{session_id}`**: Deletes a chat session history from the database.

#### Contract Scanning (Mode 1) & Dashboard
* **`POST /api/v1/contracts/scan`**: Accepts a multipart file upload (PDF/DOCX, 10MB limit), inserts a processing scan record into SQLite, and triggers the `BackgroundTasks` runner. Returns `{ "scan_id": str, "status": "processing" }` immediately.
* **`GET /api/v1/contracts/scan/{scan_id}`**: Retrieves the current status or final `ContractScanResult` JSON payload if complete.
* **`GET /api/v1/contracts/scan/{scan_id}/export`**: Streams a customized, premium PDF compliance report built with ReportLab.
* **`GET /api/v1/contracts/scans`**: Lists past scans for the dashboard's ingestion history table.
* **`GET /api/v1/dashboard/stats`**: Returns aggregate metrics: total contracts scanned, total risks identified, and total API cost (always `₹0.00`).

---

## ⏭️ Next Milestones (Frontend Development)

### Next.js Frontend Setup
Build the premium dashboard interface using Next.js, **shadcn/ui**, and **TailwindCSS** to connect to this API.
* **Authentication**: Integrate next-auth, Clerk, or handle mock logins client-side (as selected under Option A).
* **RAG Chat Panel**: Message-based interface displaying the session history sidebar using `/api/v1/chat/sessions` and showing citations in side drawers.
* **Contract Scanner Dashboard**: Drag-and-drop file upload zone feeding into `/api/v1/contracts/scan` and displaying real-time compliance meters.

