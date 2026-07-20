# Initial Design Doc — Nyaya AI: Contract Intelligence

**Author:** Mehtab Singh
**Date:** 20 July 2026
**Status:** Approved / Active Development
**Timeline:** Extended to 25 July 2026

---

## The Idea

> **Nyaya AI gives anyone in India the same contract review a ₹50,000 lawyer would give them — in 30 seconds, for free.**

Commercial contracts are drafted in opaque legalese, burying crucial risk clauses like non-competes, payment terms, or liability caps. Freelancers, startup founders, and MSME owners cannot afford high legal review costs. Consequently, they sign blind, exposing themselves to severe compliance issues.

Nyaya AI solves this by introducing a dual-mode legal workstation:
* **Mode 1 — Automatic Compliance Scan**: Automatically extracts clauses, checks statutory alignment, and flags compliance risks (e.g. MSME payment violations or void restraint-of-trade clauses).
* **Mode 2 — Legal Intelligence Chat**: A statutory and precedent RAG chat that answers legal queries with verbatim citations to official Gazette acts and Supreme Court judgments.

---

## What Makes This Different

1. **Cite-or-Refuse**: Built-in guardrails refuse queries with low confidence rather than generating hallucinations. In legal AI, citation accuracy is a trust-critical element.
2. **Grounded Multi-Source Corpus**: Integrates both official Indian Central Acts and High Court / Supreme Court precedents (`nyaya_precedents`) in Qdrant Cloud.
3. **Cloud Cascade Architecture**: Implements a cascading model workflow (Groq Llama 3.1 8B $\rightarrow$ Gemini 2.5 Flash Lite $\rightarrow$ OpenRouter Qwen 3) that delivers near-instant latency (2s) while keeping operational costs at exactly ₹0.00.

---

## Technical Approach (High Level)

```
User input (PDF / DOCX / chat question)
        │
        ▼
   Document Ingestion                      Legal Corpus
  PyMuPDF + Parser                        (Qdrant Cloud)
        │                            Statutes + Case Precedents
        ▼                                      │
   Structural Chunking                         │
 (Clause patterns, symbols)                    │
        │                                      │
        └──────────────┬───────────────────────┘
                       ▼
               Hybrid Retrieval
          (Dense BGE-M3 + Sparse)
                       │
                       ▼
                 Jina Reranker
               (Relevance Gate)
                       │
                       ▼
               Cloud LLM Cascade
             Groq ──► Gemini ──► OpenRouter
                       │
                  ┌────┴────┐
                  ▼         ▼
                Mode 1    Mode 2
             Compliance   RAG Chat
               Report    + Citations
```

**Stack**: Next.js · FastAPI · Qdrant Cloud · BGE-M3 · Jina Reranker · SQLite · SQLAlchemy · ReportLab · PyTest

---

## Technical Risks & Mitigation

* **Risk 1: Hallucinated Legal Citations**
  * *Mitigation*: Strict Pydantic schema validation (`CitedAnswer` and `RiskFinding`) requiring exact matches with retrieved chunks. Low confidence automatically triggers a refusal ("Insufficient Information").
* **Risk 2: Inference Latency**
  * *Mitigation*: Switched from local CPU Ollama inference (which took ~5 minutes) to cloud APIs (Groq and Gemini free tiers) reducing inference times to under 3 seconds. Preloaded singletons on FastAPI startup to avoid model reload delays.

---

## Timeline & Build Order

* **Week 1 (Foundation)**: Statutory ingestion of 33,000+ sections (Central Acts), dense retrieval index setup, and RAG CLI. *(Completed)*
* **Week 2 (Core Build)**: Contract chunking rules, ICA §27 & MSME payment scanners, and Cloud LLM Cascade integration. *(Completed)*
* **Week 3 (Hardening & Backend)**: Expanded corpus with DPDP Act, Mediation Act, Telecom Act, and Jan Vishwas Act. Set up the FastAPI backend and SQLite database to track sessions and scan histories, and implemented ReportLab PDF compliance report exports. *(Completed)*
* **Week 4 (Poland & Polish)**: Ingestion of custom `nyaya_precedents` dataset (Supreme Court landmark rulings) into Qdrant Cloud. Build Next.js frontend pages and integrate them with backend API routes.
* **Week 5 (Final Delivery - Due July 25)**: End-to-end testing, Loom demo recording, and final submission.
