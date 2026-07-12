# ADR-010 — Generic Contract Risk Scanner and Grounding Verification

**Date:** 2026-07-12
**Status:** Accepted
**Author:** Mehtab Singh
**Decider:** Mehtab Singh
**Depends on:** ADR-004 (LLM cascade), ADR-003 (vector DB)

---

## Context

During Stage 2 (Contract Intelligence) of building Nyaya AI, we need to design a scanner engine to identify statutory violations in uploaded contracts (such as non-compete clauses void under Indian Contract Act §27, or MSME payment terms exceeding 45 days under the MSMED Act 2006).

A contract may contain dozens of clause types, each presenting different compliance risks against the entire corpus of Indian statutory law. We need to decide how to structure the scanning engine to identify these risks.

---

## Decision Question (as posed)

> **How does the system identify legal risks in contract clauses, and how do we ensure that identified risks are legally grounded and free from hallucinations?**

---

## Proposed Options

### Option A — Dedicated Hardcoded Scan Engines
Build separate, dedicated rule-based engines for specific statutory rules (e.g. an `ICA27Engine` specifically matching non-competes, and an `MSMEEngine` specifically matching payment terms).
* **Why choose it:** Simple to implement for a few fixed rules; predictable performance.
* **Tradeoff:** Does not scale. Adding new statutory compliance checks (e.g. data localization rules under the IT Act, liability caps, or arbitration venues) requires writing custom Python code paths and hardcoding matching rules.

### Option B — Generic Corpus-Wide Scanner (Emergent Risks)
Build a single generic scanner that chunks any contract into clauses, retrieves the top-5 matching statutory provisions from the entire `nyaya_corpus` (1,021 Acts) in Qdrant, applies a permissive similarity gate to filter out irrelevant clauses, and passes the remaining clauses to the LLM cascade for joint classification and risk assessment.
* **Why choose it:** Scalable and extensible. ICA §27, MSME Act, and IT Act data localization risks emerge naturally from statutory text retrieval and LLM context analysis without hardcoded paths.
* **Tradeoff:** Slightly more complex orchestration; requires high-quality retrieval and strict prompt engineering to prevent LLM hallucinations.

---

## Decision

**Option B — Generic Corpus-Wide Scanner with Grounding Verification.**

We implement a single generic scanner that chunks the contract into clauses, indexes them, retrieves relevant laws from the entire `nyaya_corpus` in Qdrant, filters using a permissive similarity gate (`CONTRACT_RELEVANCE_THRESHOLD = 0.4`), and invokes the 3-tier LLM cascade for evaluation.

### Grounding Verification (Architectural Addition)
To strengthen the **cite-or-refuse** principle introduced in Mode 2, we introduce a strict **Grounding Verification** layer in the scanner pipeline. When the LLM cascade declares a compliance risk, its response must contain:
1. `conflicting_act`
2. `conflicting_section`
3. `conflicting_law_quote`

The scanner orchestrator normalizes these fields (stripping whitespace, punctuation, and common noise prefixes) and validates them against the retrieved statutory chunks. If the cited Act, section number, and quote cannot be successfully matched back to the retrieved context, the risk finding is rejected and dropped.

---

## Reasoning

### Why Option B (Generic Scanner) over Option A (Hardcoded Engines)
A legal intelligence product must scale beyond a couple of predefined scenarios. Contracts contain many clause types. Creating separate engines for NDA, MSA, employment, and vendor agreements is unsustainable. 
By treating compliance risk as an emergent property of retrieved statutory texts (i.e. feeding relevant laws into the LLM as context), the scanner remains completely agnostic to specific statutes. ICA §27, the MSMED Act, and the IT Act are not specialized logic paths; they are simply the laws that return high similarity scores when non-compete, payment, or data transfer clauses are evaluated. This modular design makes the engine instantly compatible with new Acts without modifying a single line of codebase.

### Why Grounding Verification is Necessary
The #1 technical risk in a legal AI platform is **hallucination** (an LLM confidently inventing a statutory section or citation). While the Chat Mode (Mode 2) handles this using strict context constraints, the Contract Scanner (Mode 1) needs a programmatic, structural safeguard.
The grounding verification step acts as a compiler-like check: it mathematically verifies that the LLM's cited authority exists in the retrieval window. By dropping ungrounded findings, we preserve the credibility of the platform.

### Gating and Status Logic
- **Relevance Gate (`0.50` threshold)**: Raised from `0.40` to filter out low-similarity noise from unrelated statutes matching standard boilerplate clauses (e.g. Delhi NCT Act or Hire Purchase Act).
- **Retrieval Breadth (`CONTRACT_RISK_TOP_K = 10`)**: Raised from `5` to `10` to resolve semantic vocabulary mismatches (e.g., target ICA §27 uses "anyone" instead of "employee", ranking it 7th). Raising top-k to `10` ensures it is included in the context window.
- **Groq Token Limit Ceiling (6,000 TPM)**: Prevents raising top-k to `15` or `20` (which causes payload sizes to exceed 6,000 tokens and triggers `413 Request too large` errors). `10` is the optimal sweet spot.
- **Evidence-Aware Statuses**:
  - `risks_found`: Grounded risks were identified.
  - `no_material_risks_found`: Clauses passed the gate and were evaluated, but no conflicts were identified.
  - `insufficient_evidence`: No clauses passed the relevance gate, indicating the system does not have relevant laws in the corpus to make a determination.
  - `ocr_required`: The PDF contains no extractable text, indicating a scanned image.

---

## Consequences

* **Emergent Compliance**: The system successfully catches non-competes, payment terms, and data localization risks purely through retrieval context and LLM analysis.
* **Security & Credibility**: Programmatically prevents the LLM from inventing fake laws or sections that weren't retrieved, maintaining high citation precision.
* **Low Operation Cost**: Reduces LLM API calls by filtering irrelevant clauses at the vector search level.
* **Storage Standard**: Transitioned Qdrant from file-based SQLite mock storage to a local Docker container (utilizing RocksDB/HNSW indexes), maintaining native performance standards.
