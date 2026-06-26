# ADR-007 — Frontend Framework and Visual Standard

**Date:** 2026-06-26
**Status:** Accepted
**Author:** Mehtab Singh
**Decider:** Mehtab Singh
**Depends on:** ADR-006 (FastAPI backend, SSE streaming, polling API)

---

## Context

Nyaya AI has two modes accessible from one interface. The frontend must handle:
- **Mode 1:** File upload (drag-and-drop), async polling for ingestion job status, risk report display with severity colour coding, citation links to source clauses
- **Mode 2:** Streaming chat responses (SSE), citation sidebar that highlights source on click, "I don't know" state when cite-or-refuse fires, session-scoped conversation memory display

Additionally, the product serves a specific trust-sensitive context. Users are uploading their legal documents — employment contracts, MSME vendor agreements, shareholder agreements. The visual register of the interface directly affects whether they trust the product enough to use it. A tool that looks like a student dashboard does not receive legal documents.

---

## Decision Question (as posed)

> **What builds the user-facing interface?**
>
> **Option A — Next.js (React)**
> Production-grade React framework. SSR/SSG, file-based routing, strong ecosystem.
> | Why choose it | Tradeoff |
> |---|---|
> | Full control over UI/UX; handles SSE natively; polling, streaming all straightforward | Requires JavaScript/TypeScript; more setup than Streamlit |
>
> **Option B — Next.js + shadcn/ui**
> Next.js with a pre-built accessible component library. Professional look without custom CSS from scratch.
> | Why choose it | Tradeoff |
> |---|---|
> | Fast to build premium-looking UI; components are copy-paste and fully customisable; no CSS framework lock-in | Still requires React knowledge; component styling decisions needed |
>
> **Option C — Vite + React (plain)**
> Faster dev server than Next.js, simpler for a SPA.
> | Why choose it | Tradeoff |
> |---|---|
> | Faster HMR, simpler mental model | No SSR; less relevant for a SPA anyway |
>
> **Option D — HTMX + Jinja2 (served from FastAPI)**
> Server-side rendered, no JavaScript framework.
> | Why choose it | Tradeoff |
> |---|---|
> | Single Python codebase | Limited interactivity for streaming chat; SSE support awkward; citation sidebar complex without React |
>
> **Agent recommendation:** Option B

---

## Decision

**Next.js + shadcn/ui.** Aesthetic quality is a product requirement, not a nice-to-have.

---

## Non-Negotiable Functional Requirements

All of the following must ship. These are not stretch goals.

| Requirement | Implementation |
|---|---|
| Drag-and-drop file upload with progress indicator | `react-dropzone` + progress bar polling `/status/{job_id}` |
| Async polling for Mode 1 job status | `useEffect` interval polling `/status/{job_id}` until `status: "complete"` |
| SSE streaming for Mode 2 chat | `EventSource` connected to `POST /chat` (SSE endpoint) |
| Citation sidebar — click citation → scroll to + highlight source clause | Citation links map to chunk IDs; document preview panel highlights on click |
| Risk panel with severity colour coding | Red (high), Amber (medium), Green (low) — semantic colour tokens, not generic CSS |
| Confidence score display per finding | Score shown as a percentage or badge on each `RiskFinding` card |
| "I don't know" state | Distinct, clearly labelled UI state when `can_answer: false` in `CitedAnswer` — not an empty response |

---

## Visual Requirements

**Theme:** Dark / deep navy. This is a legal intelligence product. The visual register must feel authoritative, trustworthy, and professional — not playful or generic.

**Reference products:** linear.app (information density, dark theme, clean typography), Perplexity AI (cited answer layout, source sidebar, confident minimalism). These are the visual benchmarks, not student dashboard templates.

**Typography:** Inter or Geist (Next.js default). Large, confident headings. Clean body copy. No decorative fonts.

**Colour palette (non-negotiable):**
- Background: deep navy (`#0A0F1E` or equivalent)
- Surface: slightly lighter navy (`#111827`)
- Accent: electric blue or teal — one strong accent colour for interactive elements
- Risk colours: semantic only — red `#EF4444`, amber `#F59E0B`, green `#10B981`
- Text: near-white (`#F9FAFB`) with muted secondary (`#9CA3AF`)

**Component treatment:** Every shadcn/ui component must be customised to this palette. Default shadcn grey boxes are not acceptable. The components are a starting point, not the output.

**Whitespace:** Generous. Legal content is dense — the UI must breathe. Padding and line-height should be set to the upper end of comfortable reading parameters.

**Trust signal:** The interface must signal competence. A user who sees a polished, dark, citation-rich interface before uploading their employment contract will trust the product. A user who sees a generic grey dashboard will not.

---

## Layout Specification

### Desktop (≥ 1024px) — Two-Panel

```
┌─────────────────────────────────────────────────────────────────┐
│  Nyaya AI                                    [nav]              │
├───────────────────────────┬─────────────────────────────────────┤
│                           │                                     │
│  SCAN PANEL               │  CHAT PANEL                        │
│  ─────────────────────    │  ─────────────────────────────     │
│  [Upload area]            │  [Chat history]                    │
│  Drag & drop or click     │                                     │
│                           │  User: Is this non-compete          │
│  [Progress indicator]     │         enforceable?                │
│                           │                                     │
│  [Risk Report]            │  Nyaya: Under ICA §27...  [cite]   │
│  ┌── HIGH ─────────────┐  │                                     │
│  │ Clause 12.3         │  │  [Citation Sidebar]                │
│  │ Non-compete         │  │  ┌────────────────────────────┐    │
│  │ ICA §27 ↗          │  │  │ Source: ICA 1872, §27      │    │
│  │ Confidence: 94%     │  │  │ "Agreements in restraint   │    │
│  └─────────────────────┘  │  │  of trade, void."          │    │
│                           │  └────────────────────────────┘    │
│  ┌── MEDIUM ───────────┐  │                                     │
│  │ Clause 8.1          │  │  [Input field]          [Send]     │
│  │ Liability cap       │  │                                     │
│  └─────────────────────┘  │                                     │
│                           │                                     │
└───────────────────────────┴─────────────────────────────────────┘
```

### Mobile (< 1024px) — Tabbed

```
┌────────────────────────────┐
│  Nyaya AI                  │
├──────────────┬─────────────┤
│  [Scan]  │  [Chat]        │  ← tabs
├────────────────────────────┤
│                            │
│  [Active panel content]    │
│                            │
└────────────────────────────┘
```

### Citation Interaction

When a user clicks a citation (in either panel):
1. The document preview panel opens (or scrolls to) the relevant page
2. The specific clause is highlighted with the accent colour
3. The citation sidebar in Mode 2 shows the verbatim quote

---

## Implementation Notes

- **Frontend reads from:** `SKILL.md` at `frontend-ui-engineering` skill before writing any component code
- **shadcn/ui install:** `npx shadcn@latest init` — select dark mode, CSS variables, Slate base colour (then override to navy)
- **Colour tokens:** Defined in `globals.css` as CSS custom properties, referenced in `tailwind.config.ts`
- **SSE client:** Native `EventSource` API, not a library — keeps the dependency count low
- **Polling:** `useInterval` hook with 1-second interval, cancelled on `status: "complete"` or error
- **Citation linking:** Each `RiskFinding` and `Citation` object contains a `chunk_id` — the frontend maps `chunk_id` to a document position and scroll target

---

## Why Aesthetic Quality Is a Product Requirement

> "Aesthetic quality is treated as a product requirement, not a nice-to-have — the target users (founders, MSME owners, freelancers) will not trust a tool that looks unpolished with their legal documents."

This is a correct product insight and it generalises: in any trust-sensitive domain (legal, financial, medical), the visual quality of the interface is a functional proxy for the product's competence. A user who sees a polished interface before uploading their employment contract makes an implicit judgement — "this product looks like it knows what it is doing." A user who sees a generic grey dashboard makes the opposite judgement, regardless of what the underlying AI produces.

The visual standard set here (linear.app / Perplexity AI register, dark navy, generous whitespace, semantic risk colours, customised shadcn components) is the minimum to clear that trust threshold for Nyaya AI's target users.

---

## Consequences

**Positive:**
- Two-panel layout clearly separates Mode 1 (scan) and Mode 2 (chat) without hiding either
- SSE streaming gives Mode 2 responses a live, intelligent feel
- Citation sidebar makes the "every answer is cited" promise visually explicit
- Dark navy theme signals legal authority — appropriate for the domain
- shadcn/ui components are accessible by default — no additional a11y work needed for keyboard navigation

**Negative / Watch:**
- Next.js adds build complexity — ensure `next.config.js` is correctly configured for SSE and large file uploads
- Citation highlighting in the document preview requires a PDF rendering library (`react-pdf` or `pdfjs-dist`) — added dependency
- Two-panel layout on mobile needs careful tab state management — ensure deep-link URLs work on mobile

---

## Alternatives Rejected

- **Option A (Next.js without shadcn):** Rejected in favour of B. Building components from scratch for a 5-week project is inefficient. shadcn gives professional-quality components as a starting point.
- **Option C (Vite + React):** Rejected. No material advantage over Next.js for this SPA; Next.js ecosystem (shadcn, deployment on Vercel) is better aligned.
- **Option D (HTMX + Jinja2):** Rejected. Cannot support SSE streaming chat with acceptable UX; citation sidebar interactivity requires JavaScript; the visual requirements cannot be met with server-side templates.
- **Streamlit:** Not formally offered as an option for the frontend — already rejected in ADR-006 as not production architecture.
