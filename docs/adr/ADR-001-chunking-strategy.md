# ADR-001 — Document Chunking Strategy

**Date:** 2026-06-26
**Status:** Accepted
**Author:** Mehtab Singh
**Decider:** Mehtab Singh

---

## Context

Nyaya AI must split contracts into retrievable pieces for both Mode 1 (automatic scan) and Mode 2 (RAG agent). Citation precision — the system's ability to say "Clause 12.3, page 4" rather than "somewhere around page 4" — depends entirely on chunk quality. A chunk that spans two clauses produces ambiguous citations. A chunk that cuts a clause in half loses legal meaning.

The system must handle:
- Well-formatted DOCX/PDF contracts with numbered clauses and headings
- Poorly formatted contracts with inconsistent structure
- Scanned images passed through OCR (PaddleOCR output), which may lose structural markers

---

## Decision Question (as posed)

> **How should Nyaya AI split contracts into retrievable pieces?**
>
> **Option A — Structural chunking (clause-boundary aware)**
> Split on clause headings, numbered sections, and schedule boundaries detected from the document structure (TOC, bold headings, numbered lists). Each chunk = one clause or sub-clause. Metadata: clause number, heading, page range.
> | Why choose it | Tradeoff |
> |---|---|
> | Citations are precise to the clause — "Clause 12.3, page 4" | Requires good document structure; breaks on poorly formatted or scanned contracts |
>
> **Option B — Semantic / sliding window chunking**
> Fixed token window (e.g. 512 tokens) with overlap (e.g. 50 tokens). No structure assumed.
> | Why choose it | Tradeoff |
> |---|---|
> | Works on any document regardless of formatting | Chunks split across clause boundaries; citations are approximate ("around page 4") |
>
> **Option C — Structural first, semantic fallback**
> Try structural chunking. If the document has no detectable structure (e.g. a scanned image with no headings), fall back to sliding window. Best of both worlds in theory.
> | Why choose it | Tradeoff |
> |---|---|
> | Handles both well-formatted contracts and poorly-scanned ones | More code to write; the fallback path has lower citation precision than Option A |
>
> **Option D — Structural first, LLM-based structural fallback**
> Try structural chunking. If the document has no detectable structure, use a small LLM to identify clause boundaries before chunking. More accurate than regex-based structural detection on edge cases.
> | Why choose it | Tradeoff |
> |---|---|
> | Highest accuracy on badly formatted documents; LLM understands legal clause structure semantically | Adds LLM cost to every ingestion on the fallback path; slower; specific LLM to be sourced |
>
> **Agent recommendation:** Option C (structural + sliding window fallback)

---

## Decision

**Structural chunking primary; LLM-based structural chunking as fallback.**

The agent recommended Option C (sliding window fallback). The student upgraded the fallback to Option D (LLM-based structural fallback) for the following reason:

Sliding window fallback produces approximate citations by design — chunks cross clause boundaries. On a legal platform where citation precision is a core product promise, an approximate fallback is not acceptable even for edge cases. An LLM-based structural fallback understands what a clause boundary *means* semantically, not just what it looks like syntactically. This produces clause-level citations even on the worst-formatted scanned contracts.

The specific LLM for the fallback chunker will be sourced from niche GitHub repositories and evaluated for accuracy vs. cost (likely a small open-source model fine-tuned for document structure parsing). This is deferred to Week 2 of implementation.

---

## Consequences

**Positive:**
- Clause-level citations on both well-formatted and poorly-formatted contracts
- No "approximate page" citations anywhere in the system
- LLM-based fallback can be upgraded independently as better models become available

**Negative / Watch:**
- LLM fallback path adds latency and cost to ingestion for structurally weak documents
- Requires sourcing and evaluating an appropriate chunking LLM (deferred decision)
- Two-path system adds complexity to the ingestion pipeline

**Implementation note:** Build and test the structural path first (Week 1). Identify and integrate the LLM fallback in Week 2 after evaluating candidates.

---

## Alternatives Rejected

- **Option B (sliding window):** Rejected. Approximate citations are a product-quality failure on a legal platform.
- **Option C (structural + sliding window fallback):** Rejected in favour of Option D — the fallback must also produce precise citations.
