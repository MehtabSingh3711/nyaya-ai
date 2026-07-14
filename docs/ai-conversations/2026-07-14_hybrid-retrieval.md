# AI Session Log — 2026-07-14 — Hybrid Retrieval Implementation

**Agent:** Antigravity (Gemini)
**Phase:** Week 4 — Hardening
**Session opened:** 19:54 IST

## Session Goal
Implement hybrid retrieval (SPLADE sparse + BGE-M3 dense + bge-reranker cross-encoder) as specified in ADR-002 and ADR-003 but deferred during CLI-first MVP. Dense-only retrieval has confirmed recall gaps: Case 2 (MSME payment term) and Case 4 (data localization) fail even at top_k=15/20, proving this is a genuine retrieval recall problem rather than a windowing issue.

## Decisions Log

### Decision: Sparse encoder choice
**Options presented:** A (BGE-M3 built-in sparse via FlagEmbedding), B (Qdrant fastembed SPLADE)
**Student chose:** BGE-M3 built-in sparse (if compatible, otherwise fastembed SPLADE). Criterion: less latency for document ingestion.
**Student's reason:** "Go with BGE M3 only if it is compatible otherwise go for the one in Qdrant. Which one will give less latency when someone ingests documents and contracts."
**Agent recommendation was:** BGE-M3 built-in sparse
**Student followed agent recommendation:** Yes
**Compatibility confirmed:** Yes — BGE-M3 via FlagEmbedding produces lexical_weights as {token_id: weight} dicts, which convert to Qdrant SparseVector(indices, values). One model, one forward pass, both dense+sparse.
**Logged at:** 2026-07-14 20:03 IST

### Decision: Reranker model
**Options presented:** bge-reranker-base (~50ms, smaller), bge-reranker-large (~200ms, higher precision)
**Student chose:** bge-reranker-base (if accuracy comparable to large)
**Student's reason:** "If the base reranker will give the almost same output accuracy then use the base"
**Agent recommendation was:** Deferred to student
**Build-time update:** Research surfaced bge-reranker-v2-m3 as outperforming both base and large while being multilingual-optimized (relevant for mixed English-Hindi legal text). Using v2-m3 instead — flagged to student.
**Student followed agent recommendation:** N/A
**Logged at:** 2026-07-14 20:03 IST

### Decision: Colab timing
**Options presented:** Ready now, or prepare script first
**Student chose:** Prepare script now, run after dinner
**Student's reason:** "Ready the script and steps for google colab gpu. I will run them after dinner"
**Logged at:** 2026-07-14 20:03 IST

## Code / Output Produced
<!-- will be filled as we implement -->

## Summary
<!-- fill in at end of session -->
