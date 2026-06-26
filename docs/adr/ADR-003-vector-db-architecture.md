# ADR-003 — Vector Database Collection Architecture

**Date:** 2026-06-26
**Status:** Accepted
**Author:** Mehtab Singh
**Decider:** Mehtab Singh
**Depends on:** ADR-002 (BGE-M3 embeddings + hybrid retrieval)

---

## Context

Nyaya AI uses Qdrant as its vector store (established by ADR-002). The question is how to structure the collections inside Qdrant. Two categories of content need to be stored and retrieved:

1. **Statutory corpus** — Indian legal Acts (ICA 1872, MSME Act 2006, IT Act 2000, IPC 1860, CPC, etc.) — persistent, versioned, shared across all users and sessions. Updated when new Acts are added; never deleted.
2. **User-uploaded contracts** — contract chunks ingested during a user session — ephemeral or session-scoped; private per user; not shared across sessions.

These two categories have different lifecycle, access patterns, and scope requirements. They must be retrievable independently (Mode 1 scans a user contract against the corpus; Mode 2 can answer from corpus alone, contract alone, or both).

Hybrid retrieval is already decided (ADR-002): BM25 sparse + BGE-M3 dense. This decision determines how that hybrid retrieval is implemented at the Qdrant layer.

---

## Decision Question (as posed)

> **Where do embeddings live, and how is the vector store structured?**
>
> **Option A — Single collection, all content**
> One Qdrant collection holds everything: statutory corpus chunks + user-uploaded contract chunks. Distinguish them by a `source_type` metadata field (`"statute"` vs `"contract"`).
> | Why choose it | Tradeoff |
> |---|---|
> | Simpler to operate; one index to manage | Can't control retrieval scope cleanly — a Mode 1 scan over a contract might retrieve irrelevant statute chunks if filters aren't perfect |
>
> **Option B — Two collections: corpus + contracts**
> `nyaya_corpus` holds statutory text — persistent, versioned, shared.
> `nyaya_contracts` holds user-uploaded contract chunks — scoped per session or per user.
> | Why choose it | Tradeoff |
> |---|---|
> | Clean separation of concerns; corpus updates don't touch user data; retrieval is scoped correctly per mode | Two indexes to manage; cross-collection retrieval (when an answer needs both statute and contract clause) requires two queries then merge |
>
> **Option C — Two collections + named vectors (Qdrant multi-vector)**
> Same two-collection structure as B, but each chunk stores multiple named vectors (`dense` from BGE-M3 and `sparse` from SPLADE/BM25). Qdrant's native hybrid search runs in a single query.
> | Why choose it | Tradeoff |
> |---|---|
> | Cleanest hybrid retrieval implementation; single query returns hybrid-ranked results natively | Requires Qdrant ≥ 1.7; slightly more complex collection config at setup |
>
> **Agent recommendation:** Option C

---

## Decision

**Option C — Two collections with named vectors.**

- `nyaya_corpus` — statutory legal corpus (persistent, versioned, shared across all users)
- `nyaya_contracts` — user-uploaded contract chunks (scoped per session)
- Each chunk in both collections stores two named vectors:
  - `dense` — BGE-M3 dense embedding
  - `sparse` — SPLADE sparse vector (BM25 equivalent, learnable)
- Qdrant's native hybrid search runs a single query over both named vectors and returns fusion-ranked results
- Cross-collection retrieval (when a Mode 2 answer requires both a statute and a contract clause simultaneously) runs two named-vector queries and merges at the application layer

---

## Reasoning

This decision is a direct architectural consequence of the hybrid retrieval choice in ADR-002 — it is not a new independent decision. Once BM25 + dense hybrid retrieval was decided, the question became: implement it as two sequential queries merged in code (brittle, more latency) or as Qdrant's native named-vector hybrid search (single query, maintained by Qdrant, cleaner). Named vectors are the correct implementation of an already-made decision.

The two-collection separation is independently correct regardless of the named-vector choice:
- The statutory corpus and user contracts have different lifecycles, different access patterns, and different scope requirements
- Mixing them in one collection requires metadata filters on every query to scope results correctly — filters can fail silently and produce wrong citations
- Separate collections make retrieval scope explicit and auditable

**Cross-collection merge at application layer:** When Mode 2 needs to answer a question that requires both a retrieved statute ("is a non-compete void under ICA §27?") and a specific contract clause ("does my contract contain such a clause?"), two named-vector queries run in parallel and their results are merged by the application layer before being passed to the LLM. This is an intentional, controlled operation — not a limitation of the architecture.

---

## Collection Schema

### `nyaya_corpus`
```
Collection: nyaya_corpus
Vectors:
  dense:  BGE-M3, dim=1024, cosine distance
  sparse: SPLADE, variable dim, dot product

Payload per chunk:
  act_name:       str   e.g. "Indian Contract Act 1872"
  section_number: str   e.g. "§27"
  section_title:  str   e.g. "Agreements in restraint of trade void"
  chapter:        str
  page:           int
  text:           str   (the chunk text)
  version:        str   corpus version tag
  source_url:     str   India Code canonical URL
```

### `nyaya_contracts`
```
Collection: nyaya_contracts
Vectors:
  dense:  BGE-M3, dim=1024, cosine distance
  sparse: SPLADE, variable dim, dot product

Payload per chunk:
  session_id:     str   UUID per upload session
  contract_type:  str   e.g. "employment", "nda", "msma_vendor"
  clause_number:  str   e.g. "12.3"
  clause_heading: str
  page:           int
  paragraph:      int
  text:           str   (the chunk text)
  ingested_at:    datetime
```

---

## Consequences

**Positive:**
- Hybrid retrieval is a single Qdrant query — no application-layer merging of BM25 + dense results
- Corpus and user data are structurally separated — no filter-based scoping risk
- Corpus can be updated (new Acts added, versions bumped) without touching user contract data
- Schema is explicit and auditable per collection

**Negative / Watch:**
- Requires Qdrant ≥ 1.7 for named vector support — pin the version in requirements
- SPLADE sparse vectors require a SPLADE encoder model alongside BGE-M3 — additional model to load at ingestion time
- Cross-collection queries add one network round-trip — acceptable at current scale, monitor under load in Week 4

---

## Alternatives Rejected

- **Option A (single collection):** Rejected. Metadata-filter-based scoping is brittle and can fail silently — wrong citations in a legal product are a trust-destruction event.
- **Option B (two collections, no named vectors):** Rejected in favour of C. Named vectors implement the already-decided hybrid retrieval natively. Option B would require merging BM25 and dense results in application code — more fragile, more latency, more maintenance.
