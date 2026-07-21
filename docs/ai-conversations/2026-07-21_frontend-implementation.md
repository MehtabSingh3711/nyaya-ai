# AI Session Log — 2026-07-21 — Next.js Frontend Porting & Integration
**Agent:** Antigravity (Gemini)
**Phase:** Week 5 — Hardening & Ship
**Session opened:** 2026-07-21T13:40:00+05:30

## Session Goal
Translate static HTML mockup templates inside `/design-templates` into a production-grade, secure Next.js App Router frontend, fully integrated with all active FastAPI backend endpoints.

## Decisions Log

### Decision: User Authentication Field Mapping
* **Options presented:** Email Address vs. Username compatibility.
* **Student chose:** Option B (visually display "Email Address" in inputs, but programmatically map the payload value to the backend's `username` parameter to maintain compatibility and ease future GoogleAuth integration).
* **Agent recommendation was:** Option B.
* **Student followed agent recommendation:** Yes.

### Decision: Route Protection Mechanism
* **Options presented:** Client-side localStorage checks vs. Server-side Middleware cookie inspection.
* **Student chose:** Cookie-based Server Middleware to prevent layout flashing and ensure secure route protection in production.
* **Agent recommendation was:** Cookie-based Server Middleware.
* **Student followed agent recommendation:** Yes.

### Decision: Case Precedents Scope
* **Options presented:** Display everywhere vs. Restrict to Contract Scanner.
* **Student chose:** Case precedents should be rendered strictly in the Contract Scanner findings workstation, keeping RAG Chat grounded purely in central statutes.
* **Agent recommendation was:** Restrict to Contract Scanner.
* **Student followed agent recommendation:** Yes.

### Decision: Custom PNG Logo Implementation
* **Options presented:** Inline SVG recreation vs. Dual PNG logo asset swapping based on active CSS classes.
* **Student chose:** Dual PNG logo swapping via CSS (`block dark:hidden` and `hidden dark:block`), referencing files under `frontend/assets/` to ensure zero hydration shifts.
* **Agent recommendation was:** Dual PNG logo swapping.
* **Student followed agent recommendation:** Yes.

### Decision: Pipelined Streaming Contract Scanner
* **Options presented:** Option A (generator-based small-batch streaming queue with live UI updates) vs. Option B (small-batch runs saving results at the end).
* **Student chose:** Option A (Pipelined generator-based streaming with live UI updates to flatten CPU spikes and show findings instantly).
* **Agent recommendation was:** Option A.
* **Student followed agent recommendation:** Yes.

---

## Code / Output Produced
* **Created components & configuration**:
  * [NyayaLogo.tsx](file:///c:/Users/mehta/Downloads/summer-internship/nyaya-ai/frontend/src/components/NyayaLogo.tsx): Smart PNG-asset switching logo element.
  * [Header.tsx](file:///c:/Users/mehta/Downloads/summer-internship/nyaya-ai/frontend/src/components/Header.tsx): Unified top navigation bar, now featuring interactive dropdown notifications.
  * [api.ts](file:///c:/Users/mehta/Downloads/summer-internship/nyaya-ai/frontend/src/lib/api.ts): Axios interceptors injection client.
  * [middleware.ts](file:///c:/Users/mehta/Downloads/summer-internship/nyaya-ai/frontend/src/middleware.ts): Server-side Next.js routing guard.
* **Optimized Backend RAG Pipeline**:
  * [scanner.py](file:///c:/Users/mehta/Downloads/summer-internship/nyaya-ai/nyaya_ai/contracts/scanner.py): Refactored the core audit engine into a generator queue processing clauses in batches of 2 with a staggered 1-second delay between cross-encoder calls to handle API rate limits.
  * [tasks.py](file:///c:/Users/mehta/Downloads/summer-internship/nyaya-ai/nyaya_ai/api/tasks.py): Integrated streaming queue scanner into Celery/local task runners to commit progress iteratively.
  * [reranker.py](file:///c:/Users/mehta/Downloads/summer-internship/nyaya-ai/nyaya_ai/retrieval/reranker.py): Offloaded cross-encoder reranking to Jina Cloud Reranker API with exponential retry backoff and local ONNX lazy-load fallback.
  * [config.py](file:///c:/Users/mehta/Downloads/summer-internship/nyaya-ai/nyaya_ai/config.py): Exposed `JINA_API_KEY` configurations.
  * [main.py](file:///c:/Users/mehta/Downloads/summer-internship/nyaya-ai/nyaya_ai/api/main.py): Modified scan GET endpoint to return findings results during `"processing"` state.
* **Polished User Interface (Next.js)**:
  * [scan/page.tsx](file:///c:/Users/mehta/Downloads/summer-internship/nyaya-ai/frontend/src/app/scan/page.tsx): Added live rendering support for partial results, dynamic header status pulse styling, right sidebar flex-col alignment fixes, and initial loading spinner gates.
  * [signin/page.tsx](file:///c:/Users/mehta/Downloads/summer-internship/nyaya-ai/frontend/src/app/signin/page.tsx): Bound all logo assets to route back to landing page.
  * [README.md](file:///c:/Users/mehta/Downloads/summer-internship/nyaya-ai/frontend/README.md): Instructions to configure and run the frontend.

---

## What the Student Built / Decided
You successfully ported the entire mockup design system to Next.js and integrated it live with the FastAPI/Celery backend. Facing local laptop crashes under heavy local models, you decided to offload reranking to Jina's Cloud API (retaining a lazy ONNX fallback) and restructured your scanning loop into a generator-driven queue processing clauses in batches of 2 with a 1-second staggered delay. You also adjusted the backend routes and the Next.js polling loop to stream analysis findings onto the dashboard live in real-time, delivering an extremely responsive and hardware-safe compliance scanner.

---

## Open Questions for Next Session
* Deploying the Next.js frontend to Vercel and the FastAPI backend to Render's free tier.
* Implementing the RAGAS evaluation framework to profile system accuracy and citation rates.

## Next Session Goal
Set up hosting for the application (Vercel + Render) and configure the RAGAS evaluation harness.
