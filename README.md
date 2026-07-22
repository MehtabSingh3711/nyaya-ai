# Nyaya AI (न्याय AI) — Indian Legal Intelligence Platform
> **Know what you sign.** Production-grade Indian contract risk intelligence & multi-statute legal RAG.

---

[![FastAPI](https://img.shields.io/badge/FastAPI-0.111.0-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-14.2.35-000000?style=flat-square&logo=next.js)](https://nextjs.org/)
[![Qdrant](https://img.shields.io/badge/Qdrant-Vector_DB-dc2626?style=flat-square&logo=qdrant)](https://qdrant.tech/)
[![BGE-M3](https://img.shields.io/badge/Embeddings-BGE--M3_Dense%2BSparse-blue?style=flat-square)](https://huggingface.fr/BAAI/bge-m3)
[![License](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](LICENSE)

---

## 🎬 Live Demo & Walkthrough

* **Live Frontend**:http://localhost:3000
* **Demo Video Walkthrough**: [5-Minute Loom Video Walkthrough](https://loom.com)

---

## 📌 Problem Statement

Every day, Indian freelancers, MSMEs, and startups sign contracts containing unenforceable or illegal clauses. Under **Section 27 of the Indian Contract Act, 1872**, post-employment non-compete clauses are completely void. Under **Section 15 & 16 of the MSME Development Act, 2006**, payment terms exceeding 45 days are illegal and incur mandatory 3x bank-rate interest penalties. 

**Nyaya AI** bridges this gap by providing:
1. **Mode 1 (Contract Intelligence)**: Automated clause-by-clause contract risk scanning against 33,603 sections of Indian law and landmark case precedents.
2. **Mode 2 (Legal Intelligence Chat)**: Natural language Q&A across 1,021 Indian Acts with strict "Cite-or-Refuse" zero-hallucination guardrails.

---

## 🏗️ System Architecture

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

## 🛠️ Tech Stack

| Component | Technology / Model | Why Chosen |
|---|---|---|
| **Frontend** | Next.js 14, React, TailwindCSS | Modern App Router, fast SSR, custom glassmorphism design |
| **Backend** | FastAPI, Python 3.11, Uvicorn | Async performance, Pydantic v2 validation, OpenAPI docs |
| **Vector Database** | Qdrant (Qdrant Cloud + Local) | Native dense + sparse hybrid vector support with payload filtering |
| **Embeddings** | BAAI/bge-m3 (1024-dim) | Unified dense + sparse lexical vectors in a single pass |
| **Reranker** | BAAI/bge-reranker-v2-m3 | PyTorch CUDA cross-encoder reranking on Kaggle GPU 1 (<25ms) |
| **LLM Cascade** | Groq (Llama 3.1 8B) $\rightarrow$ Gemini 2.0 Flash $\rightarrow$ OpenRouter | 3-tier zero-cost fallback cascade (~1.8s latency, ₹0 cost) |
| **Database** | SQLite + SQLAlchemy | Lightweight relational storage for user accounts & chat history |
| **Caching** | Redis | Instant response times for repeated legal queries |

---

## 🚀 Quickstart Guide

### Prerequisites
* Python 3.10+
* Node.js 18+
* Git

### 1. Clone & Set Up Backend

```bash
git clone https://github.com/MehtabSingh3711/nyaya-ai.git
cd nyaya-ai

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file from template
cp .env.example .env
```

Set your API keys in `.env`:
```env
GROQ_API_KEY=your_groq_api_key
GEMINI_API_KEY=your_gemini_api_key
REMOTE_EMBEDDING_URL=https://your-kaggle-cloudflare-url.trycloudflare.com  # Optional
```

Run the FastAPI server:
```bash
uvicorn nyaya_ai.api.main:app --reload --port 8000
```

### 2. Set Up Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000` in your browser.

### 3. Run Test Suite

```bash
# Run 88+ unit and integration tests
pytest tests/ -v
```

---

## 📊 Evaluation & Accuracy

* **Citation Precision**: **95.8%**
* **Hallucination Protection**: Grounded "Cite-or-Refuse" guardrails verified
* **Clause Extraction F1**: **92.4%**
* **Average Scan Speed**: **~2.1s per clause** (via Groq Tier 1 + Kaggle Dual-GPU)
* **Cost Per Contract**: **₹0.00** (100% Free Tiers)

See detailed metrics in [docs/accuracy_and_evaluation.md](docs/accuracy_and_evaluation.md).

---

## 📂 Data Sources & Documentation

* **Statutory Corpus**: 33,603 sections across 1,021 Indian Acts (`mratanusarkar/Indian-Laws`).
* **Case Law Precedents**: Landmark Supreme Court and High Court judgments (`nyaya_precedents` collection).
* **Architectural Decisions (ADR 001–008)**: Detailed in [docs/thinking_artifact.md](docs/thinking_artifact.md).
* **System Architecture**: Detailed in [docs/architecture.md](docs/architecture.md).
* **Presence Artifact**: Blog post in [docs/presence_artifact.md](docs/presence_artifact.md).
* **Resume Bullets**: ATS-optimized bullets in [docs/resume_bullets.md](docs/resume_bullets.md).
* **Mock Interview Q&A**: 10 technical Q&As in [docs/mock_interview.md](docs/mock_interview.md).

---

## 🛣️ Roadmap & Future Scope

1. **Multi-Language Support**: Support for Hindi, Tamil, and Marathi legal translations.
2. **Asynchronous Multi-Page Audits**: Celery + Redis queues for 200+ page M&A agreements.
3. **Enterprise RLS & Multi-Tenancy**: AWS Aurora PostgreSQL integration with tenant-isolated Qdrant namespaces.

---

## 📄 License & Acknowledgements

This project is licensed under the **MIT License**.  
Developed as part of the B.Tech CSE-AIDE (Applied AI & Intelligent Systems) Internship Program, 2026.
