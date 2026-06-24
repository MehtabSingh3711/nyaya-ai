# Problem Statement — Nyaya AI: Contract Intelligence

**Project:** Nyaya AI — Indian Legal Intelligence Platform
**Module:** Contract Intelligence (Internship Scope)
**Author:** Mehtab Singh
**Date:** 23 June 2026
**Mentor Review Due:** 26 June 2026

---

## 1. Business Scenario

**The imagined company:** Nyaya AI is a legal intelligence platform built for
the Indian market. The name comes from न्याय — Sanskrit for *justice*, and the
Indian school of logical reasoning. The tagline is *Know what you sign.*

**The company's pain:** India has over 63 million MSMEs, tens of millions of
freelancers, and a growing class of startup founders and early employees who
sign legally binding contracts every week. A contract review by a qualified
lawyer costs ₹5,000–₹50,000, takes 2–7 days, and assumes the user already
understands enough to brief the lawyer. For most working Indians, none of those
conditions are met.

The result is a structural access gap. The person signing their first employment
agreement does not know that the non-compete in Schedule 3 is likely void under
Indian Contract Act §27. The MSME vendor does not know that the 90-day payment
term violates the MSME Development Act 2006 and that they have a statutory
remedy. The freelancer does not know that the IP assignment clause covers all
future work in the same domain. They sign. The consequence surfaces months
later — when they take a new client, miss a payment window, or receive a legal
notice. At that point, the signed document is the ground truth.

**Why this problem matters:** The legal protections exist. ICA §27 has voided
non-competes since 1872. The MSME Act mandates 45-day payment since 2006.
These are not gaps in the law — they are gaps in access to the law. Nyaya AI's
job is to close that gap at the moment it matters: before the signature.

---

## 2. Problem Statement

You are being asked to build the Contract Intelligence module of Nyaya AI:
a production-grade system that allows any Indian user to upload a contract and
receive, within seconds and at negligible cost, a precise analysis of what they
agreed to, what is legally risky or void under Indian law, and exactly what
to push back on.

**Specifically, you will deliver:**

- A document ingestion pipeline capable of processing PDFs (native and scanned)
  and DOCX files for Indian contracts
- A hybrid retrieval system (BM25 + dense vector embeddings) over contract text
  with structural chunk awareness (clause numbers, headings, schedules)
- A three-tier LLM cost cascade (Phi-3 Mini → Gemma-2-9B → GPT-4o) that
  escalates only on low confidence, targeting < ₹0.50 per contract at p95
- Five specialised analysis engines:
  - **ICA §27 Enforcement Engine** — detects non-compete clauses, flags as
    likely void, outputs clause + page + legal reasoning + negotiation stance
  - **MSME Payment Term Detector** — flags payment terms > 45 days, cites
    MSME Development Act 2006, outputs clause + violation + statutory remedy
  - **Semantic Clause Diff Engine** — compares two contract versions,
    surfaces what changed and what became riskier
  - **Agentic Batch Sweep** — scans a folder of contracts for a
    natural-language query with ranked results
- A live evaluation dashboard reporting: citation precision > 90%,
  hallucination rate < 5%, extraction F1 > 0.88, cost per contract < ₹0.50
- A working frontend (upload → analyse → results with citations)

Every finding the system produces must cite the exact clause text, page and
paragraph reference, and the Indian statutory or case-law basis. Unsupported
assertions are a failure mode, not a minor issue.

---

## 3. Why This Matters for Placements

This project is scoped to produce a portfolio signal that is directly legible to
technical interviewers at three specific targets:

**SpotDraft** — India's leading contract intelligence platform. SpotDraft does
exactly what Nyaya AI does, at enterprise scale. Building a production-grade
version of their core product — with Indian-law-specific clause detection,
hybrid retrieval, structured Pydantic extraction, and a real eval harness — is
the strongest possible portfolio signal for an AI/ML engineering role there.
The domain overlap is total. You are not demonstrating adjacent skills; you are
demonstrating the exact skill set they hire for.

**Sarvam AI** — India's leading AI lab, focused on Indian-context and
Indian-language AI. Nyaya AI demonstrates domain-specific RAG, structured
extraction, LLM cascade design, and production evaluation — the class of
problems Sarvam works on. The Indian-law specificity (ICA, MSME Act) shows
you understand that Indian-context AI is not just English AI with a different
dataset.

**Razorpay** — A product company serving over 8 million MSMEs. The MSME
Payment Term Detector is directly relevant to Razorpay's core user base.
This project shows you can build AI that operates within a specific regulated
market with real legal consequences — not a demo, a production system with
eval numbers.

The combination of legal domain depth, production system design (cost
constraints, citation requirements, eval targets), and Indian market specificity
produces a project that is difficult to replicate and immediately understood by
interviewers at all three.

---

## 4. Technical Direction

This is not a tutorial project. The topics below are the map — each one
represents an area where you will make defensible technical decisions, not
follow a recipe.

| Area | What you need to own |
|------|---------------------|
| **Document parsing** | PyMuPDF for native PDFs; PaddleOCR for scanned images; Unstructured.io for DOCX; structural extraction (clause numbers, headings, schedules) |
| **Chunking strategy** | Structural-first (split on clause boundaries); semantic fallback (sliding window with overlap) when structure is absent; metadata preservation per chunk |
| **Embeddings** | BGE-M3 — multilingual, strong on legal text; understand why this over OpenAI embeddings for Indian-law context |
| **Vector database** | Qdrant — local-first, production-ready, supports hybrid search natively |
| **Retrieval** | BM25 + dense hybrid retrieval; cross-encoder reranking; understand precision vs. recall tradeoff for legal citations |
| **LLM cascade** | Phi-3 Mini (fast, cheap, handles simple extraction) → Gemma-2-9B (mid-tier) → GPT-4o (complex reasoning, last resort); confidence scoring to trigger escalation |
| **Structured extraction** | Pydantic v2 + JSON mode; every extraction is a typed schema with validation, not a free-text blob |
| **Evaluation** | RAGAS for retrieval + generation quality; custom citation precision metric; hallucination detection; cost tracking per query |
| **Backend** | FastAPI; async endpoints; file upload handling; structured error responses |
| **Frontend** | Upload interface; streaming results display; citation highlighting |
| **Observability** | Langfuse for LLM tracing; log every cascade decision, every retrieval result, every eval score |
| **Indian law specifics** | ICA §27 (non-competes); MSME Development Act 2006 (payment terms); standard Indian contract structure conventions |

The depth required is: understand the tradeoffs, implement the system, explain
every decision in an interview. Not: reproduce a tutorial.

---

## 5. Scope Boundaries

### In Scope

| Contract Types | Six types |
|---------------|-----------|
| NDA | Non-Disclosure Agreement |
| MSA | Master Service Agreement |
| Employment Agreement | Including offer letters with binding clauses |
| MSME Vendor Agreement | Supply contracts, payment terms |
| SHA | Shareholder Agreement |
| Freelancer Contract | Service agreements, IP assignment, non-compete |

- Indian law jurisdiction only
- Minimum 200 contracts in the evaluation dataset
- English-language contracts (primary); mixed English-Hindi acceptable
- Documents up to ~50 pages

### Explicitly Out of Scope

- Criminal law analysis (FIR analysis, IPC sections, bail conditions)
- Court judgment summarisation
- Regulatory compliance filings (SEBI, RBI, MCA)
- Multi-lingual contracts in regional languages (Hindi-only, Tamil-only)
- Real-time regulatory update monitoring
- Court filing assistance or legal advice

These are planned as future modules on the same platform. The architecture
must allow them to plug in without rewriting the core pipeline.

### Bonus (if time permits)

- Hindi-English mixed contract support
- WhatsApp or Telegram bot interface for upload
- Confidence interval display per finding
- Batch processing UI for law firm use

---

## 6. Final Deliverable Shape

What the shipped product looks like at the end of 5 weeks:

**User flow:**
1. User opens the web interface and uploads a contract (PDF or DOCX)
2. System processes and returns within ~30 seconds:
   - A plain-language summary of what the contract says
   - A risk panel — flagged clauses with severity (high / medium / low)
   - For each flagged clause: the exact clause text, page reference, the
     legal issue, the Indian statutory basis, and a suggested negotiation stance
3. User can optionally upload a second version of the same contract to trigger
     the semantic diff engine
4. Evaluation dashboard (separate view or README) shows live eval metrics
   on the test set: citation precision, hallucination rate, F1, cost per contract

**What goes in the GitHub repo:**
- `/backend` — FastAPI application, all pipeline components
- `/frontend` — Web interface
- `/evaluation` — RAGAS eval harness, custom citation metric, results
- `/docs` — Problem statement, design doc, architecture, ADRs, session logs
- `/data` — Contract dataset manifest (actual contracts excluded from repo if
  not openly licensed)
- `README.md` — Eval numbers (real, not estimated), setup instructions,
  architecture diagram, demo link or Loom recording

**The demo moment (60 seconds):**
Upload an employment contract. The system flags a non-compete clause.
It says: *"Clause 12.3 contains a non-compete restriction. Under Indian
Contract Act §27, agreements restraining trade are void. This clause is likely
unenforceable. Suggested response: request removal of Clause 12.3 or replace
with a narrowly scoped non-solicitation clause."* Citation: page 4, paragraph 3.

That is the demo. That is what Nyaya AI ships.

---

*This problem statement was produced in Session 1 of the Nyaya AI internship
on 23 June 2026, following the structured discovery protocol in AGENTS.md.*
