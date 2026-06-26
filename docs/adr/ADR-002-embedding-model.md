# ADR-002 — Embedding Model and Reranking Layer

**Date:** 2026-06-26
**Status:** Accepted
**Author:** Mehtab Singh
**Decider:** Mehtab Singh

---

## Context

Nyaya AI requires dense vector embeddings for hybrid retrieval across two Qdrant collections:
1. The statutory legal corpus (ICA 1872, MSME Act, IT Act, IPC, CPC, etc.)
2. User-uploaded contract chunks (per session)

The embedding model must handle:
- Legal English (archaic in older Indian statutes like ICA 1872 and IPC 1860)
- Mixed English-Hindi contract clauses (common in MSME vendor agreements)
- Long clause-level chunks (some Indian contract clauses run 300–600 tokens)
- Local execution — legal document contents are sensitive and should not leave the infrastructure

Citation precision is the #1 product requirement. The embedding model determines retrieval quality, which determines whether the system retrieves the right clause to cite.

---

## Decision Question (as posed)

> **What embedding model generates the vectors that power retrieval for both Mode 1 and Mode 2?**
>
> **Option A — BGE-M3 (BAAI)**
> Multilingual dense embedding model. Natively supports 100+ languages including Hindi. Strong on long documents and domain-specific text. Open-source, runs locally.
> | Why choose it | Tradeoff |
> |---|---|
> | Best-in-class for multilingual + legal text; no API cost; runs locally in Qdrant | Larger model (~570M params); slower than smaller models; needs GPU for fast inference at scale |
>
> **Option B — OpenAI text-embedding-3-small / large**
> Commercial API. Fast, reliable, strong benchmarks across domains.
> | Why choose it | Tradeoff |
> |---|---|
> | Zero infra to manage; fast; easy to swap models | API cost per embedding (adds up over 200+ contracts); data leaves your infra; not fine-tunable |
>
> **Option C — Voyage AI (voyage-law-2)**
> A legal-domain-specific embedding model. Purpose-built for legal retrieval. Strong citation precision on legal benchmarks.
> | Why choose it | Tradeoff |
> |---|---|
> | Highest precision on legal text specifically; best for citation accuracy | Commercial API only; relatively new; smaller community; cost; data leaves your infra |
>
> **Option D — Cohere embed-multilingual-v3**
> Multilingual commercial embeddings with strong Indian-language support.
> | Why choose it | Tradeoff |
> |---|---|
> | Good multilingual coverage; simple API | API cost; data leaves infra; less legal domain specificity than Voyage |
>
> **Agent recommendation:** Option A (BGE-M3)

---

## Decision

**BGE-M3 for embeddings, running locally via HuggingFace + Qdrant FastEmbed.**
**bge-reranker-large added as a cross-encoder reranking layer on top of retrieval.**

---

## Reasoning

### Why BGE-M3

All API-based options (B, C, D) were evaluated and rejected on a shared set of criteria:

| Rejection criterion | Applies to |
|---|---|
| Data leaves infrastructure — legal contract contents are sensitive | B, C, D |
| Ongoing API cost on every reindex (200+ contracts × future corpus growth) | B, C, D |
| No local control or fine-tuning path | B, C, D |
| Vendor dependency — rate limits, pricing changes, deprecation risk | B, C, D |

BGE-M3 satisfies all requirements:
- Multilingual (100+ languages, including Hindi) — handles mixed English-Hindi contract clauses
- Runs locally via HuggingFace + Qdrant FastEmbed — zero data egress, zero API cost
- Strong performance on long legal text (clause-level chunks at 300–600 tokens)
- Open-source — auditable, fine-tunable, no vendor lock-in

### Why Voyage AI (Option C) was specifically evaluated and rejected

Voyage `voyage-law-2` was the strongest commercial alternative. It was built specifically for legal retrieval and would likely produce higher raw citation precision than BGE-M3 on English legal text.

**Rejection reasons:**
1. **API-only** — no local deployment option. Legal contract contents cannot leave the infra.
2. **Reindexing cost** — every new contract ingestion, every corpus update triggers API calls. At 200+ contracts and a growing statutory corpus, this becomes material.
3. **Data sovereignty** — user-uploaded contracts contain sensitive commercial terms. Sending them to a third-party API introduces legal and confidentiality risk for the product's own users.
4. **Citation precision gap addressed elsewhere** — the gap between BGE-M3 and a legal-specific embedding model is addressed by adding `bge-reranker-large` as a cross-encoder reranking step. The reranker re-scores the top-k retrieved chunks with full attention over the query + chunk pair, which recovers precision that a weaker embedding model loses.

### Why bge-reranker-large

After first-stage retrieval (BM25 + BGE-M3 dense, hybrid), the top-k candidates are re-scored by `bge-reranker-large` — a cross-encoder that reads the full query and each candidate chunk together. This is significantly more accurate than embedding similarity alone, and it runs locally. The additional latency (~100–200ms per rerank pass on CPU) is acceptable for the response times targeted.

---

## Consequences

**Positive:**
- Zero data egress — all contract and statutory content stays local
- Zero ongoing embedding cost — no API calls on ingestion or reindexing
- Full retrieval stack runs locally: BGE-M3 (dense) + BM25 (sparse) + bge-reranker-large (rerank)
- Voyage-level citation precision recovered via reranking without Voyage's infra constraints

**Negative / Watch:**
- BGE-M3 (~570M params) requires a GPU for fast batch embedding during ingestion. Development: Colab/Kaggle T4. Production: Railway GPU instance or equivalent.
- bge-reranker-large adds ~100–200ms per response on CPU. Monitor under load in Week 4.
- If fine-tuning becomes necessary (on Indian legal text specifically), that work is non-trivial but remains an option.

---

## Alternatives Rejected

- **Option B (OpenAI text-embedding-3):** Rejected — data leaves infra, ongoing cost, no local control.
- **Option C (Voyage voyage-law-2):** Rejected — API-only, data sovereignty risk, reindexing cost. See detailed reasoning above.
- **Option D (Cohere multilingual-v3):** Rejected — same API constraints as B and C; less legal domain specificity than even Voyage.
