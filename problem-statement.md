# Problem Statement — C1: Nyaya AI — Contract Intelligence

**Project:** Nyaya AI — Indian Legal Intelligence Platform
**Module:** Contract Intelligence (Internship Scope)
**Author:** Mehtab Singh
**Date:** 20 July 2026
**Extended Timeline:** 25 July 2026

---

### 1. Business Scenario

A startup founder, freelancer, or MSME owner receives a standard commercial contract from a counterparty. These documents are drafted by corporate lawyers in dense, opaque legalese. Important terms like non-compete clauses, payment schedules, liability caps, and dispute resolution paths are often buried deep within the text under confusing terminology. 

For these individuals, hiring a professional legal counsel to review the agreement is prohibitively expensive (often costing between ₹5,000 to ₹50,000 per review) and takes several days. Consequently, they sign the agreement without understanding the legal risks. The consequences—such as a legal threat, a missed payment remedy, or a lost client—only surface months later when the signed contract is treated as the ground truth.

You will build **Nyaya AI** — a production-grade Indian legal intelligence platform that automatically parses these documents, identifies structural risks, and answers legal queries with inline citations to both statutory codes and case-law precedents.

---

### 2. Problem Statement

Build **Nyaya AI — Contract Intelligence** — a two-mode legal intelligence platform:

#### **Mode 1 — Automatic Compliance Scan**
* **Ingestion**: PDF (native + scanned) and DOCX contracts parsed via PyMuPDF and OCR tools, chunked at structural clause boundaries.
* **Extraction**: Schema-validated JSON extraction of core variables (parties, dates, amounts, governing law, term, termination, liability cap, non-compete, payment terms) using Pydantic v2.
* **Compliance Engines**:
  * **ICA §27 Enforcement Engine**: Detects non-compete covenants, flags them as void under Section 27 of the Indian Contract Act, 1872, and provides recommended negotiation stances.
  * **MSME Payment Term Detector**: Flags payment cycles exceeding the statutory 45-day limit under Section 15 of the MSME Development Act, 2006, and outlines the interest penalties (3× bank rate).
  * **Statutory Risk Flags**: Assesses clauses against post-2021 acts, highlighting risks related to data protection (DPDP 2023), mediation rules (Mediation Act 2023), and telecommunication licenses (Telecom Act 2023).

#### **Mode 2 — Legal Intelligence RAG Chat**
* **Statutory Corpus**: Grouped, versioned legal data hosted on Qdrant Cloud:
  * *Statutes*: Indian Contract Act 1872, MSME Development Act 2006, IT Act 2000, IPC, CPC, DPDP Act 2023, Mediation Act 2023, and Telecommunications Act 2023.
  * *Case Law Precedents*: Ingested collection of landmark Supreme Court and High Court judgments (`nyaya_precedents`) covering key contract disputes.
* **Retrieval Pipeline**: Hybrid search (dense BGE-M3 + sparse token weight matching) on Qdrant Cloud, reranked via Jina Reranker v1 Turbo.
* **Grounding & Citations**: Every RAG answer includes inline citations to the exact Act and Section (statutory) or Case Name and Year (precedent).
* **Hallucination Guard (Cite-or-refuse)**: The system returns "Insufficient Information" when confidence falls below the gate threshold, protecting users from fabricated citations.

#### **Shared Infrastructure**:
* **LLM Cost Cascade**: Escalates queries through a ₹0-cost cascade:
  1. *Tier 1*: Groq (Llama 3.1 8B Instant) — instant execution.
  2. *Tier 2*: Gemini (2.5 Flash Lite via OpenAI-compatible endpoint) — complex reasoning.
  3. *Tier 3*: OpenRouter (Qwen 3 Next 80B Free) — fallback.
* **Database & API**: FastAPI backend with background tasks and local SQLite storage for multi-session chat and scan history tracking.

---

### 3. Why This Matters for Placements

Legal AI has the most immediate ROI in the GenAI space. Companies like **SpotDraft, Leegality, and Sarvam AI** are building verticalized domain-specific RAG models for the Indian legal sector. Tech companies like **Razorpay, Swiggy, and Swapp** rely on automated vendor and merchant compliance pipelines. Demonstrating a project with hybrid dense-sparse vector databases, rerankers, a structured extraction evaluation harness, and a cost-effective API cascade makes your profile highly competitive for Applied AI and ML Engineer positions.

---

### 4. Technical Direction

* **Document parsing**: PyMuPDF and Unstructured.io for extraction; chunking by section symbols (`§`) and clause patterns.
* **Embeddings & Vector DB**: BGE-M3 (dense + sparse named vectors) in Qdrant Cloud.
* **Reranking**: Jina Reranker v1 Turbo for exact semantic validation.
* **Extraction**: Pydantic v2 schema-enforcement (`CitedAnswer`, `RiskFinding`).
* **LLM Cascade**: Confidence thresholding to route requests between Groq and Gemini.
* **Database**: SQLAlchemy 2.0 with SQLite for session persistence.
* **Observability**: Tracing logs for retrieval metrics and LLM responses.

---

### 5. Scope Boundaries

* **In scope**: PDF/DOCX contracts; Mode 1 and Mode 2; core statutes (ICA, MSME, DPDP, Mediation, Telecom, Jan Vishwas); Supreme Court case law precedents; eval reports; FastAPI backend and Next.js frontend.
* **Out of scope**: Criminal court filings, real-time regulatory compliance alerts, multi-tenant subscription tiers.

---

### 6. Final Deliverable Shape

* **GitHub Repository**: Complete codebase containing `/nyaya_ai` API packages, tests, and configuration files.
* **Web Application**: Next.js interface containing the upload scanner, risk analysis panel, RAG chat panel, and chat history.
* **ADR Set**: 5 ADRs documenting architecture, cascading models, and DB structures.
* **Loom Walkthrough**: A 5-minute video demonstrating a contract upload, risk flag details, and PDF report export.
* **Evaluation Report**: Verification scores for citation precision and F1 extraction metrics.
