# Initial Design Doc — Nyaya AI: Contract Intelligence

**Author:** Mehtab Singh
**Date:** 24 June 2026
**Status:** Draft — for mentor review
**Due:** 24 June 2026

---

## The Idea

> **Nyaya AI gives anyone in India the same contract review a ₹50,000 lawyer would give them — in 30 seconds, for free.**

A contract review by a qualified Indian lawyer costs ₹5,000–₹50,000 and takes 2–7 days. For most working Indians — gig workers, MSME owners, freelancers, first-time employees — that review never happens. They sign. The consequence surfaces months later when the non-compete lands, the payment window closes, or the legal notice arrives.

Nyaya AI closes that gap with a two-mode platform:

- **Mode 1 — Automatic Scan:** Upload a contract. Get a structured risk report in ~30 seconds — flagged clauses, legal basis, negotiation stance, cited to the exact page and paragraph.
- **Mode 2 — Legal Intelligence Chat:** Ask plain-language questions about a contract or about Indian law generally. Get grounded, cited answers from a structured Indian legal corpus. No answer without a source.

---

## What Makes This Different

Most "AI for legal" products are wrappers around a generic LLM. They hallucinate confidently and cannot tell you *where in the law* a claim comes from.

Nyaya AI is built differently in three ways:

1. **Cite-or-refuse.** If retrieved evidence is below confidence threshold, the system outputs "I don't know" — not a fabricated legal claim. In a legal product, one wrong citation destroys trust permanently. The cite-or-refuse logic is architectural, not a patch.

2. **Shared legal corpus as foundation.** Both modes retrieve from the same versioned Indian legal corpus (statutes, Acts). Mode 1's scan engines and Mode 2's conversational agent are built on top of one retrieval infrastructure — not duplicated. New legal domains (criminal law, regulatory compliance) plug in by expanding the corpus, not rebuilding the pipeline.

3. **Indian law specificity.** ICA §27 (non-competes void since 1872), MSME Development Act 2006 (45-day payment mandate), IPC 1860 — these are not generic legal concepts. The system knows Indian law, Indian contract structure, and Indian legal language.

---

## Technical Approach (High Level)

```
User input (PDF / DOCX / chat question)
        │
        ▼
  Document ingestion                     Legal corpus
  PyMuPDF + PaddleOCR                   (Qdrant collection 1)
  + Unstructured.io                      ICA 1872, MSME Act,
        │                                IT Act, IPC, CPC
        ▼                                      │
  Structural chunking                          │
  (clause-boundary aware)                      │
        │                                      │
        └──────────────┬────────────────────────┘
                       ▼
              Hybrid retrieval
              BM25 + BGE-M3 dense
              + cross-encoder rerank
                       │
                       ▼
              LLM cost cascade
              Phi-3 Mini → Gemma-2-9B → GPT-4o
              (escalate on low confidence)
                       │
                  ┌────┴────┐
                  ▼         ▼
            Mode 1        Mode 2
         Risk report    Cited answer
        + citations   + session memory
```

**Stack:** FastAPI · Qdrant · BGE-M3 · Pydantic v2 · Langfuse · RAGAS

---

## The #1 Risk

**Hallucinated legal citations.**

An LLM stating that a clause "violates ICA §27" when the retrieved context does not actually support that claim is not a minor accuracy issue — it is a trust-destruction event. A user who acts on a fabricated legal claim and is wrong has been harmed by the product.

**Mitigation (built in from Week 1):**
- Every claim requires a retrieved source passage above a confidence threshold
- Below threshold → system outputs "I don't know" with an explanation of what it could and could not find
- RAGAS citation-precision metric in the eval harness measures this explicitly
- Target: hallucination rate < 5% on the 100-question test set

---

## Build Order and Week 1 Milestone

**Why Mode 2 first:** The legal corpus — chunked, embedded, and indexed in Qdrant — is the foundation that Mode 1's scan engines sit on top of. Building the retrieval infrastructure once, correctly, before adding the scan engines avoids duplication and forces the citation logic to be right from the start.

**By end of Week 1 (27 June), demoable:**

> Upload the Indian legal corpus (ICA 1872, MSME Act 2006, IT Act 2000, IPC 1860, Code of Civil Procedure). Ask: *"Is a non-compete clause enforceable in India?"* System returns a cited answer: ICA §27, plain-language explanation, confidence score. "I don't know" path tested and working.

**Week 2:** Mode 1 scan engines (ICA §27 detector, MSME payment term detector) built on top of the same retrieval index.
**Week 3:** Semantic diff engine, agentic batch sweep, eval harness.
**Week 4:** Frontend, observability, eval report.
**Week 5:** Hardening, demo polish, documentation.

---

## Open Questions

1. **Corpus licensing:** ICA 1872 and older statutes are public domain. MSME Act 2006, IT Act 2000, IPC 1860 — need to confirm the source (India Code / bare acts) is permissible to index.
2. **Scanned contract quality:** PaddleOCR accuracy on low-quality scans may hurt citation precision. Need to test on a sample of real scanned contracts in Week 1.
3. **Confidence threshold calibration:** The cite-or-refuse threshold needs to be tuned against the eval set — starting value TBD after first eval run.

---

*This design doc was produced in Session 1 of the Nyaya AI internship on 24 June 2026.*
