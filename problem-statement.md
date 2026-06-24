# Problem Statement — C1 (Enhanced): Nyaya AI — Contract Intelligence

**Project:** Nyaya AI — Indian Legal Intelligence Platform
**Module:** Contract Intelligence (Internship Scope)
**Author:** Mehtab Singh
**Date:** 23 June 2026
**Mentor Review Due:** 26 June 2026

---

### 1. Business Scenario

You are the **AI Engineer at "LexAssist", an Indian legal-aid nonprofit** that helps gig workers, MSME owners, freelancers, and first-time employees navigate contracts they cannot afford a lawyer to review. The organisation runs free contract clinics in Bengaluru and Delhi — but demand is 10× the capacity of their volunteer lawyers. The CEO says: *"We turn away 400 people a week. They go home and sign whatever they were given."*

The real problem is structural. A non-compete void under ICA §27 looks identical on the page to an enforceable one. A 90-day payment term that violates the MSME Development Act 2006 does not announce itself. An uncapped liability clause in a freelancer contract does not come with a warning label. The documents are drafted by the counterparty's lawyers, in language designed to be opaque. The user signs. The consequence — a legal threat, a missed payment remedy, a lost client — surfaces months later when the signed document is the ground truth.

You will build **Nyaya AI** — a production-grade Indian legal intelligence platform that closes this gap at scale. *Know your rights.*

---

### 2. Problem Statement

Build **Nyaya AI — Contract Intelligence** — a two-mode legal intelligence platform:

**Mode 1 — Automatic Scan**
- **Ingestion:** PDF (native + scanned), DOCX contracts — PyMuPDF + PaddleOCR + Unstructured.io; clause-level structural chunking
- **Extraction:** structured fields (parties, dates, governing law, term, termination, liability cap, non-compete, payment terms) — schema-validated JSON via Pydantic v2
- **Risk engines — four run automatically on every upload:**
  - **ICA §27 Enforcement Engine:** detect non-compete clauses, flag as likely void, output clause + page + legal reasoning + negotiation stance
  - **MSME Payment Term Detector:** flag payment terms > 45 days, cite MSME Development Act 2006, output clause + violation + statutory remedy
  - **Semantic Clause Diff Engine:** upload 2 contract versions → surface what changed and what got riskier
  - **Agentic Batch Sweep:** scan a folder of contracts for a natural-language query with ranked results
- **Hallucination guard:** output "I don't know" when evidence is weak; confidence score per finding

**Mode 2 — Legal Intelligence Chat (RAG Agent)**
- **Knowledge base:** The platform is powered by an embedded Indian legal corpus — a structured, versioned knowledge base of Indian statutes and acts that both the automatic scan engines and the conversational agent retrieve from. Contract Intelligence is the first module built on this corpus. The architecture is designed for new legal domains to plug in by expanding the corpus and adding domain-specific engines, without rebuilding the retrieval infrastructure.
  - *Minimum viable corpus (Week 1):* ICA 1872, MSME Development Act 2006, IT Act 2000, IPC 1860, Code of Civil Procedure
  - *Extended corpus (Week 3 if time permits):* Consumer Protection Act, Arbitration and Conciliation Act, Industrial Disputes Act, SEBI regulations
  - User-uploaded contracts indexed per session; Qdrant with two collections (statutory corpus + user documents)
- **RAG pipeline:** hybrid retrieval (BM25 + dense BGE-M3) + cross-encoder reranking; every answer grounded in a retrieved statute or clause, not generated from memory
- **Chat interface:** user asks plain-language questions — *"Is this non-compete enforceable?"*, *"What does clause 8.2 mean?"*, *"What's my remedy for a late payment?"*
- **Citations on every turn:** statute name + section, or document name + clause + page — no answer without a source
- **Session memory:** follow-up questions retain context within a session

**Shared infrastructure:**
- **LLM cost cascade:** Phi-3 Mini → Gemma-2-9B → GPT-4o; escalate on low confidence; target < ₹0.50 per contract at p95
- **Eval harness:** 100+ Q&A pairs with ground truth; RAGAS + custom citation-precision metric; measure hallucination rate, extraction F1, cost per query

---

### 3. Why This Matters for Placements

Legal AI is the #1 vertical where GenAI has clear, measurable ROI. **SpotDraft, Leegality, IndusLaw** and every Indian legal-tech team are hiring for exactly this. **Sarvam AI** (India's leading AI lab) hires for Indian-context domain-specific RAG — this project demonstrates that directly. **Razorpay** serves 8M+ MSMEs; the MSME Payment Term Detector is a product demo, not a side feature.

Demonstrates RAG done right, structured extraction, LLM cascade cost engineering, agentic design, and a real eval harness — the full AI engineering stack, not just a chatbot wrapper.

---

### 4. Technical Direction

**Topics you must cover (at working depth):**
- **Document parsing:** PyMuPDF, PaddleOCR, Unstructured.io; structural vs semantic chunking; clause-boundary detection
- **Embeddings & vector DB:** BGE-M3 (multilingual, strong on legal text); Qdrant with two collections — statutory corpus + user docs; understand why BGE-M3 over OpenAI for Indian-law context
- **Retrieval:** hybrid BM25 + dense; cross-encoder reranking (bge-reranker); precision vs recall tradeoff for legal citation
- **Extraction:** Pydantic v2 + JSON mode; structured output with validation; every field is a typed schema
- **LLM cascade:** confidence scoring to trigger escalation; cost tracking per query; same cascade serves both modes
- **RAG agent:** stateful conversation; session memory; query routing (is this about an uploaded doc or a general legal question?); cited response formatting per turn
- **Knowledge base design:** ingestion pipeline for Indian statutes; versioning; how to add a new Act without reindexing everything
- **Eval:** RAGAS framework; custom citation-precision metric; hallucination detection; walk-forward eval on the test set
- **Backend:** FastAPI; async endpoints; file upload; chat session management
- **Frontend:** two-mode interface — scan panel + chat panel with citation sidebar
- **Observability:** Langfuse for LLM tracing; log every cascade decision, retrieval result, chat turn, and eval score
- **Indian law specifics:** ICA §27 (non-competes since 1872); MSME Development Act 2006 (45-day payment mandate); standard Indian contract clause conventions

**Stretch (pick at least one):**
- Fine-tune a small model (Phi-3 / Qwen2.5) on Indian contract extraction schema
- Multi-lingual support (Hindi/English mixed contracts)
- WhatsApp or Telegram interface for Mode 2

---

### 5. Scope Boundaries

- **In scope:** PDF/DOCX contracts (6 types: NDA, MSA, Employment, MSME Vendor, SHA, Freelancer); both modes; knowledge base (ICA 1872, MSME Act 2006, IT Act minimum); 200+ contract eval dataset; eval harness; web UI
- **Out of scope:** criminal law (FIR, IPC), court judgment research, regulatory filings (SEBI/RBI/MCA), e-signature, contract authoring, multi-tenant, real-time regulatory monitoring
- **Bonus:** fine-tuned extractor; Hindi-English mixed contracts; WhatsApp/Telegram bot; confidence interval display per finding

---

### 6. Final Deliverable Shape

- **Repo:** `/backend` (FastAPI, pipeline, chat session API) · `/frontend` (scan + chat modes) · `/knowledge-base` (ingestion pipeline + statutory corpus) · `/evaluation` (RAGAS harness, custom metrics, results) · `/docs` (problem statement, design doc, architecture, ADRs, session logs) · `/data` (contract dataset manifest)
- **Hosted web app** with two modes accessible from the same interface
- **Eval report:** 100+ test cases, citation precision, hallucination rate, extraction F1, cost per query — real numbers
- **5 ADRs:** chunking strategy, embedding model choice, vector DB design, LLM cascade thresholds, knowledge base versioning
- **README:** eval numbers (real, not estimated), architecture diagram, setup instructions, demo link
- **Loom walkthrough** (5 min): upload a contract → Mode 1 flags ICA §27 non-compete → switch to Mode 2 → ask a follow-up → cited answer appears

**The 60-second demo:**
Upload an employment contract. Mode 1 flags Clause 12.3: *"Likely void under ICA §27. Suggested response: request removal or replace with a narrowly scoped non-solicitation clause."* Citation: page 4, paragraph 3. Switch to Mode 2. Ask: *"Can my employer enforce this?"* The agent cites the same clause and §27, explains the remedy. Two modes. One platform. Every answer cited.

---

*This problem statement was produced in Session 1 of the Nyaya AI internship
on 23 June 2026, following the structured discovery protocol in AGENTS.md.*
