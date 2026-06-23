# Deliverables Specification — 3rd Year Batch (B.Tech CSE-AIDE)

**Duration:** 22 June 2026 → 26 July 2026 (5 weeks)
**Mode:** Individual work. No grouping.
**Companion to:** 01_Workflow_Guide.md, 02_Technical_Problem_Compendium.md

---

## The Big Idea

Every student — regardless of segment, problem statement, tech stack — submits the **same shape** of deliverables. This is deliberate. It means:

- Your resume looks the same structure to a recruiter
- The evaluation rubric is consistent and fair
- You can compare across segments easily (for showcase, awards, etc.)
- The certificate carries the same weight

The **content** of every deliverable is segment-specific (see Doc 02). The **shape** is universal.

---

## The Three Categories of Deliverables

You will submit, by **26 July 2026, 11:59 PM IST**:

| Category | Count | Weight | What it shows |
|----------|-------|--------|---------------|
| **Weekly Deliverables** | 4 weekly submissions | 30% | Consistent execution, communication cadence |
| **Milestone Deliverables** | 2 major submissions | 50% | Depth, completeness, production-grade quality |
| **Final Deliverables** | 1 final submission | 20% | Polish, communication, presence |

Plus **2 mandatory soft deliverables** (not graded but required to pass):
- The certificate-eligibility check (explained at the end)
- The interview-readiness package (a personal artifact, not graded)

---

# PART 1 — WEEKLY DELIVERABLES (4 weeks × 1 submission)

Every **Saturday, 11:59 PM IST**, you submit a weekly deliverable. Format: a **single GitHub Issue** in your project repo, titled `Week N Submission — <your name> — <problem code>`, with a checklist completed.

These are small but **non-negotiable**. Missing one is a -2.5% on your final grade per miss.

---

## Week 1 (Due Sat 4 July 2026, 11:59 PM)

**Theme:** Foundation laid. Data flowing. Architecture signed off.

### Required in the GitHub Issue

- [ ] **Repo created and public.** Link.
- [ ] **README.md** with: project name, one-line description, problem-statement code, segment name, your name, target roles.
- [ ] **Initial Architecture Diagram** (C4 Level 1 or a hand-drawn equivalent). Embedded as image or linked.
- [ ] **Tech stack table.** Component | Choice | Why (one line). Example: `Vector DB | Qdrant | open source, self-hostable, hybrid search`.
- [ ] **Data layer working.** A screenshot or terminal output showing data ingested + queried.
- [ ] **5 GitHub commits** minimum on the main branch.
- [ ] **Friday demo video** (5 min, Loom) recorded. Link.
- [ ] **One-pager status** at the end of the issue:
  - What's done: …
  - What's stuck: …
  - Next week's 3 goals: …

### What "done" looks like
You could be hit by a bus on Sunday and someone could read your README and pick up where you left off.

---

## Week 2 (Due Sat 11 July 2026, 11:59 PM)

**Theme:** End-to-end "skinny" version of the product works. Ugly UI is fine. Functionality is not.

### Required in the GitHub Issue

- [ ] **End-to-end demo.** Screenshot or 3-min screen recording of the full product working on a small slice of the problem.
- [ ] **Updated architecture diagram** (now showing actual components used, not planned).
- [ ] **First ADR (Architecture Decision Record).** Template:
  ```
  # ADR-001: <Title>
  ## Context
  <what we're deciding and why>
  ## Decision
  <what we chose>
  ## Consequences
  <trade-offs, both positive and negative>
  ## Alternatives considered
  <what we rejected and why>
  ```
- [ ] **10 GitHub commits** total on main.
- [ ] **Friday demo video** (5 min, Loom). Link.
- [ ] **Status one-pager** (same format as Week 1).

### What "done" looks like
A non-technical friend could watch your demo video and say "I get what this does."

---

## Week 3 (Due Sat 18 July 2026, 11:59 PM)

**Theme:** Hardening. Tests, observability, the boring stuff that wins interviews.

### Required in the GitHub Issue

- [ ] **Tests added.** At least 3 unit tests + 1 integration test, with passing CI (screenshot of green CI).
- [ ] **README polished.** A reviewer can clone → set up → run in <15 min.
- [ ] **Logging + error handling.** A `try/except pass` audit. None allowed in critical paths.
- [ ] **2 more ADRs.** (Total of 3 ADRs now.)
- [ ] **15 GitHub commits** total on main.
- [ ] **Friday demo video** (5 min, Loom). Link.
- [ ] **First blog post OR written artifact** (see "Thinking Artifact" in Doc 01) — draft or final, your choice.
- [ ] **Status one-pager.**

### What "done" looks like
A senior engineer reviewing your PR would say "this is mergeable."

---

## Week 4 (Due Sat 25 July 2026, 11:59 PM)

**Theme:** Ship it. Deployed. Documented. Defended.

### Required in the GitHub Issue

- [ ] **Live deployment URL.** A real, working URL (free-tier is fine).
- [ ] **5-min Loom walkthrough** of the deployed product. Public or unlisted.
- [ ] **All 3 ADRs finalised.** 1 more can be added (encouraged).
- [ ] **20 GitHub commits** total on main.
- [ ] **Blog post OR written artifact final** — submitted as a separate file (`thinking_artifact.md` or `.pdf`).
- [ ] **Resume bullets draft.** 3-4 bullets about this project, in the standard "Action verb + tech + outcome" format.
- [ ] **Status one-pager.**

### What "done" looks like
A recruiter, in 7 minutes, can: clone your repo, see the live URL, read your README, watch your Loom, and skim your blog post. They will have everything they need to decide to interview you.

---

# PART 2 — MILESTONE DELIVERABLES (2 major submissions)

These are **the** deliverables. The ones that get evaluated most heavily. Submit them on the dates below via a **final GitHub Release** (tagged `v1.0-milestone-1` and `v1.0-milestone-2`) with the assets attached.

---

## MILESTONE 1 — The "Alpha" Build (Due Sun 19 July 2026, 11:59 PM)

**Theme:** "If a recruiter cloned this right now, the core would work."

### What to submit (GitHub Release `v1.0-milestone-1`)

| # | Asset | Format | Notes |
|---|-------|--------|-------|
| 1 | **Public GitHub repo** | URL | All code, all commits, clean history |
| 2 | **README.md** | Markdown in repo root | See "README Standard" below |
| 3 | **Architecture diagram** | PNG/SVG in `/docs` | C4 Level 2 (containers) + a one-page narrative |
| 4 | **Demo video (5 min)** | Loom link in README | Walk through the deployed product, narrate trade-offs |
| 5 | **Test report** | `/docs/test_report.md` | What was tested, results, what's not |
| 6 | **ADR set** | `/docs/adr/` | 3 ADRs minimum, in standard format |
| 7 | **Live deployment URL** | In README | Must be live; uptime not guaranteed but must be reachable at submission |
| 8 | **Data sources documented** | `/docs/data.md` | What data, where from, license, schema |

### README Standard (enforced)
A reviewer must be able to go from `git clone` → running product in 15 minutes. Mandatory sections:

```
1. Project Title + 1-line tagline
2. Demo (Loom embed + live URL)
3. Problem statement (1 paragraph)
4. Architecture diagram
5. Tech stack (table)
6. Quickstart
   - Prerequisites
   - Install
   - Run
   - Test
7. Data
8. ADRs (link to /docs/adr/)
9. Known limitations
10. Roadmap (what's next if you had 2 more weeks)
11. License + Acknowledgements
```

### Evaluation rubric (Milestone 1)

| Dimension | Weight | What "5/5" looks like |
|-----------|--------|----------------------|
| Technical depth | 30% | Code works end-to-end; architecture sound; ADRs are thoughtful |
| Product sense | 20% | Solves a real problem; UX is intentional, not accidental |
| Engineering hygiene | 30% | Repo, README, tests, deploy, ADRs, observability — all there |
| Communication | 20% | Loom is clear, README is honest, diagrams are not stock templates |

---

## MILESTONE 2 — The "Final" Build (Due Sat 25 July 2026, 11:59 PM)

**Theme:** "I'd put this on my resume with zero hesitation."

### What to submit (GitHub Release `v1.0-final`)

Everything from Milestone 1, **plus:**

| # | Asset | Format | Notes |
|---|-------|--------|-------|
| 9 | **Thinking Artifact** | `thinking_artifact.md` or `.pdf` in `/docs` | 1500-3000 words. See "Thinking Artifact Spec" below |
| 10 | **Presence Artifact** | Blog URL OR public talk recording | See "Presence Artifact Spec" below |
| 11 | **Resume bullets** | `resume_bullets.md` in `/docs` | 3-4 bullets, polished |
| 12 | **Mock-interview Q&A** | `mock_interview.md` in `/docs` | 10 questions an interviewer might ask, with your answers |
| 13 | **Postmortem (optional but high-credit)** | `postmortem.md` in `/docs` | One real bug you hit and how you fixed it; what you'd do differently |

### Thinking Artifact Spec

Pick ONE of these (your choice):

**Option A — The Deep-Dive Blog Post (1500-3000 words)**
- Pick a non-obvious technical decision in your project
- Explain: the problem, the options, your choice, the trade-offs, what you'd do with more time
- Audience: a senior engineer at a product company who hasn't seen your code
- Publish on Medium / dev.to / Hashnode / personal blog

**Option B — The Architecture Decision Record Set (5-8 ADRs)**
- Treat the 5-8 ADRs as the artifact
- Each ADR ~500 words, technical, opinionated
- Cover: tech stack, architecture, data model, scaling, security, observability
- Read together, they form a coherent narrative

**Option C — The Postmortem + Lessons**
- Pick 1-2 real problems you hit (model didn't converge, pipeline failed silently, deployment broke)
- For each: timeline, root cause, fix, prevention, what it taught you
- ~1500 words

**Option D — The "How I'd Build This for Real" Memo**
- 1500-3000 words
- Pretend the company that the problem statement imagines gave you 6 months and a team of 3
- Describe the production architecture, the team, the roadmap, the risks
- This is your "product thinking + engineering" display

### Presence Artifact Spec

Pick ONE:

**Option A — Published Blog Post (Medium / dev.to / Hashnode / personal)**
- 1200+ words
- Public URL
- About your project, the problem, the build, the result
- Include screenshots, code snippets, the Loom demo

**Option B — Loom Walkthrough Series (3-5 videos, 5-10 min each)**
- Each covers a different angle: problem framing, architecture, code walkthrough, demo, lessons
- Public or unlisted
- All linked in a single `presence_artifact.md`

**Option C — Public Talk Recording**
- 15-20 min lightning talk OR a 45-min deep-dive
- Recorded, uploaded to YouTube (can be unlisted)
- Audience: students + early-career engineers
- Submit: video URL + slides (PDF)

**Option D — Open-Source Release with a "Wow" README**
- Your repo, but with a README so good it could be a Medium post
- Includes a GIF demo at the top, an architecture diagram, a "Why I built this" section, an "If you're hiring, here's what this shows" section

### Evaluation rubric (Milestone 2)

Same as Milestone 1, with weights:

| Dimension | Weight | What's new |
|-----------|--------|------------|
| Technical depth | 25% | Same as M1, plus the thinking artifact shows technical maturity |
| Product sense | 25% | Same as M1, plus presence artifact shows you can talk about your work |
| Engineering hygiene | 20% | Same as M1 |
| Communication | 30% | **Upweighted** — M2 is where writing + presenting shines |

---

# PART 3 — FINAL SUBMISSION (Due Sun 26 July 2026, 11:59 PM)

### What to submit

| # | Asset | Format |
|---|-------|--------|
| 1 | **Final GitHub Release** `v1.0-showcase` | All of M2, plus any polish |
| 2 | **Final Loom (3 min)** | The "elevator pitch" version. What's the project, why does it matter, what did you build, what's next. |
| 3 | **Updated resume** | `resume_final.md` and a PDF version. The project is on the top line. |
| 4 | **Self-evaluation form** | Google Form (link will be shared). 10 questions, 15 min to fill. |
| 5 | **Showcase slide (1 slide)** | PNG or PDF, used in the public showcase |

### Self-evaluation form (preview)

You'll be asked:
1. Segment chosen, problem chosen, why.
2. What you're most proud of.
3. What you'd redo if you started over.
4. What role you're now best positioned for.
5. Rate your comfort (1-5) on: SQL, Python, cloud, Docker, the core tech of your segment, communication.
6. Which company would you interview at tomorrow with this portfolio?
7. What's the next 90 days of self-development for you?
8. (Optional) Anything you want the internship lead to know.

This isn't graded individually, but it's read carefully. It informs the showcase and the certificate.

---

# PART 4 — MANDATORY (BUT UNGRADED) CHECKS

## Certificate Eligibility

To receive the **internship certificate**, all of the following must be true:

- [ ] All 4 weekly deliverables submitted on time
- [ ] Milestone 1 submitted (graded)
- [ ] Milestone 2 submitted (graded)
- [ ] Final submission made (graded)
- [ ] You have NOT submitted any work that was not done during 22 June – 26 July 2026
- [ ] Your repo is public OR shared with a designated reviewer with a written explanation
- [ ] You attended at least 3 of 4 Friday demos (or watched the recordings and submitted a 1-paragraph summary)

The certificate is **segment-specific**, e.g.:
- *Certificate of Internship in Insights & Decision Intelligence*
- *Certificate of Internship in Data Platform & Pipeline Engineering*
- *Certificate of Internship in Applied AI & Intelligent Systems*
- *Certificate of Internship in MLOps & Production ML*
- *Certificate of Internship in LLM Systems & Applied GenAI*
- *Certificate of Internship in Cloud-Native & Platform Engineering*

A generic "Internship Completion" certificate is **not** issued.

---

## Interview-Readiness Package (Not Graded)

This is a **personal artifact** you keep for yourself. Build it during the last 3 days of the internship.

- A **1-page "project sheet"** (PDF) — the same content as your showcase slide, formatted for sending in cold emails
- A **2-min Loom** — the "30-second-elevator-pitch" expanded to 2 minutes
- A **list of 20 companies you'd apply to** with this project, and the specific role
- A **30-day post-internship plan** — what you'll do to extend the project or build a second one

You don't submit this. You use it.

---

# Submission Logistics

## Where to submit

| Deliverable | Submission channel |
|-------------|---------------------|
| Weekly deliverables | GitHub Issue in your project repo (issue template will be provided) |
| Milestone 1 | GitHub Release `v1.0-milestone-1` + form |
| Milestone 2 | GitHub Release `v1.0-final` + form |
| Final | GitHub Release `v1.0-showcase` + form |
| All forms | Google Forms (links shared Day 1) |

## Deadlines (consolidated)

| Date | What |
|------|------|
| 24 Jun, 11:59 PM | Initial Design Doc (1 page) |
| 26 Jun, 11:59 PM | Final architecture + tech stack sign-off |
| 4 Jul, 11:59 PM | Week 1 submission |
| 11 Jul, 11:59 PM | Week 2 submission |
| 18 Jul, 11:59 PM | Week 3 submission |
| 19 Jul, 11:59 PM | **Milestone 1 (Alpha)** |
| 25 Jul, 11:59 PM | Week 4 submission |
| 25 Jul, 11:59 PM | **Milestone 2 (Final)** |
| 26 Jul, 11:59 PM | **Final Submission + Showcase** |

**Late policy:** -10% per day, max 3 days. After 3 days, the submission is not accepted for grading (counts as missed for certificate eligibility). Extensions granted only for documented emergencies, via internship lead.

---

# The "If You're Stuck" Ladder

A clear escalation path so you don't go silent:

1. **Stuck for < 24 hours** → Search the cohort Slack, ask in #help, try the docs.
2. **Stuck for 24-48 hours** → Open a "Help Request" GitHub Issue in your repo. Mentor responds within 24 working hours.
3. **Stuck for > 48 hours** → Schedule a 1:1 with your segment mentor (office hours Wed/Fri 4-5 PM, or by appointment).
4. **Stuck for > 1 week on a blocker** → Reach out to the internship lead directly. We will help you scope down or pivot the problem statement.

Going silent is the **only** failure mode. Stuck-and-asking is fine. Stuck-and-quiet is not.

---

# Evaluation Philosophy

We are not grading whether you "completed" the problem. We are grading whether you **shipped a defensible artifact**.

A "simple" project that's clean, tested, documented, deployed, and explained well will outscore a "complex" project that's spaghetti, untested, README-less, and unrunnable.

The grading bias is: **clarity over cleverness, completeness over complexity, communication over code volume.**

You have 5 weeks. You can do this. Pick, plan, ship.

See you on 22 June.
