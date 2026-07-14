# ADR-011 — Hybrid Retrieval Reinstatement

**Date:** 2026-07-14
**Status:** Accepted
**Author:** Mehtab Singh
**Decider:** Mehtab Singh
**Depends on:** ADR-002 (BGE-M3 embeddings), ADR-003 (vector DB architecture)
**Amends:** ADR-002, ADR-003 (reinstates deferred components)

---

## Context

During the CLI-first MVP (Weeks 0–3), hybrid retrieval was explicitly deferred from the architecture specified in ADR-002 and ADR-003. The implemented retrieval was dense-only: BGE-M3 1024-dimensional cosine similarity, no sparse vectors, no cross-encoder reranking.

During Mode 1 (Contract Intelligence) validation in Week 4, dense-only retrieval demonstrated **confirmed recall gaps**:

| Validation Case | Expected Statute | Dense-Only Result (top_k=15) | Dense-Only Result (top_k=20) |
|---|---|---|---|
| Case 1: Non-compete clause | ICA 1872 §27 | ✅ Found | ✅ Found |
| Case 2: MSME 90-day payment term | MSME Act 2006 §15 | ❌ Not found | ❌ Not found |
| Case 3: Clean NDA (no risk) | No match expected | ✅ Correct | ✅ Correct |
| Case 4: Data localization clause | IT Act 2000 §43A | ❌ Not found | ❌ Not found |

**Key finding:** Widening top_k from 5 → 15 → 20 did NOT fix Cases 2 or 4. This confirms the issue is **genuine recall failure** in the dense embedding space — the correct sections are not ranking highly enough at any practical k, not that they're just outside a narrow window.

This is exactly the failure mode that hybrid retrieval was designed to address: sparse/lexical matching captures exact statute names and section numbers that dense embeddings can miss, and cross-encoder reranking eliminates false-positive-adjacent noise.

---

## Decision

**Reinstate the full hybrid retrieval pipeline** as originally specified in ADR-002 and ADR-003:

1. **Sparse vectors:** BGE-M3 built-in lexical weights (not separate SPLADE model)
   - Produces both dense and sparse vectors in a single forward pass
   - Halves encoding time compared to running two separate models
   - Lexical weights converted to Qdrant SparseVector format

2. **Hybrid search:** Qdrant prefetch + RRF (Reciprocal Rank Fusion)
   - Dense prefetch: BGE-M3 cosine similarity, top-20
   - Sparse prefetch: lexical weight dot product, top-20
   - Server-side RRF fusion → combined ranked list

3. **Cross-encoder reranking:** bge-reranker-v2-m3
   - Reads full (query, candidate) pair jointly with attention
   - Re-scores top-20 hybrid candidates → top-5 for LLM
   - Chosen over bge-reranker-base/large: v2-m3 is multilingual-optimized
     (relevant for mixed English-Hindi legal text) and outperforms both
     on modern benchmarks

---

## Retrieval Pipeline (Updated)

```
Query (question or clause text)
       │
       ▼
Encode: BGE-M3 (dense 1024d + sparse lexical weights, single pass)
       │
       ▼
Hybrid search (single Qdrant query_points call):
  prefetch[0]: dense cosine, top-20
  prefetch[1]: sparse dot product, top-20
  fusion: RRF → combined top-20
       │
       ▼
Cross-encoder rerank: bge-reranker-v2-m3
  Reads (query, "Act §Section: chunk_text") pairs
  Re-scores → top-5
       │
       ▼
Top-5 chunks passed to LLM cascade (Mode 2)
  or relevance gate + risk assessment (Mode 1)
```

---

## Implementation Details

### Sparse encoder choice: BGE-M3 built-in vs. separate SPLADE

**Options considered:**
- **A — BGE-M3 lexical weights:** Single model produces both dense and sparse vectors in one forward pass via FlagEmbedding's `BGEM3FlagModel.encode(return_sparse=True)`. Output is `{token_string: weight}` dict, converted to `SparseVector(indices, values)` via tokenizer.
- **B — Qdrant fastembed SPLADE (`prithivida/Splade_PP_en_v1`):** Separate model for sparse encoding, requires additional model download and separate forward pass.

**Chosen:** Option A. Single forward pass means ~50% less encoding time for ingestion (33,603 sections) and query-time encoding. No second model to download, load, or maintain.

### Reranker choice: bge-reranker-v2-m3 vs. base vs. large

**Options considered:**
- **bge-reranker-base:** ~110MB, ~50ms on CPU, good accuracy
- **bge-reranker-large:** ~560MB, ~200ms on CPU, slightly higher accuracy
- **bge-reranker-v2-m3:** ~560MB, ~100-150ms on CPU, multilingual, outperforms both base and large on modern benchmarks

**Chosen:** v2-m3. The multilingual capability is directly relevant for Indian legal text which contains mixed English-Hindi terms. Performance is between base and large in latency but exceeds both in accuracy.

### Collection schema change

The `nyaya_corpus` collection was recreated with:
```python
vectors_config={"dense": VectorParams(size=1024, distance=COSINE)}
sparse_vectors_config={"sparse": SparseVectorParams()}
```

This required a full re-embed and re-upsert of all 33,603 sections on Colab T4 GPU, as Qdrant collection schemas are immutable after creation and sparse vectors cannot be added incrementally to existing points.

---

## Consequences

**Positive:**
- Sparse lexical matching captures exact statute names and section numbers that dense embeddings miss
- RRF fusion combines the strengths of semantic similarity (dense) and keyword matching (sparse)
- Cross-encoder reranking eliminates false-positive-adjacent noise (e.g., "Hire Purchase Act" matching when ICA §27 is relevant)
- Full retrieval stack runs locally — no API calls, no data egress
- Both Mode 1 and Mode 2 share the same search() function — the change propagates to both modes automatically

**Negative / Watch:**
- Full re-embedding required (~60-80 min on Colab T4 GPU) whenever the corpus changes
- Cross-encoder adds ~100-150ms per query on CPU — monitor under load
- FlagEmbedding dependency added alongside sentence-transformers
- bge-reranker-v2-m3 downloads ~560MB on first run (cached afterward)

---

## Alternatives Rejected

- **Increase top_k further (e.g., 50, 100):** Rejected. The issue is not windowing — it's that the correct sections don't rank highly in pure dense embedding space at any practical k. Increasing k would also flood the LLM with irrelevant context.
- **Fine-tune BGE-M3 on Indian legal text:** Rejected for now. Fine-tuning requires training data and is non-trivial. Hybrid retrieval + reranking is the standard solution for domain-specific recall gaps and should be tried first.
- **BM25 via separate index (Elasticsearch/tantivy):** Rejected in favor of Qdrant-native sparse vectors. Avoids adding another service to the stack.
