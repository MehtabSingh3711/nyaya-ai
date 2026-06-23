# Internship Workflow Guide — 3rd Year Batch (B.Tech CSE-AIDE)

**Duration:** 22 June 2026 → 26 July 2026 (5 weeks, ~25 working days)
**Mode:** Individual work. No teams. No group projects.
**Outcome:** 1 deep production-grade project + 2 supporting artifacts, all interview-defensible.

---

## 1. The Big Picture

You are not here to "learn a topic." You are here to **ship a product** that a real company would be embarrassed to NOT put in front of a recruiter. Every choice you make — segment, problem statement, tech stack, deployment — should pass one test: *"Can I defend this in a 45-minute technical interview and a 10-minute live demo?"*

The internship has three layers, and you will work on all three **in parallel** every week:

| Layer | What it is | Why it matters |
|------|-----------|---------------|
| **Build Layer** | The product you ship | Resume + demo + interview |
| **Thinking Layer** | The PRD, ADRs, design docs, postmortems | Shows you can think like an engineer, not just code |
| **Presence Layer** | GitHub, LinkedIn, Loom demos, blog posts | Gets you noticed before the interview |

---

## 2. The 6 Segments (Pick ONE)

| # | Segment Name | Target Job Roles |
|---|--------------|------------------|
| 1 | **Insights & Decision Intelligence** | Data Analyst, Business Analyst, BI Analyst, Analytics Consultant |
| 2 | **Data Platform & Pipeline Engineering** | Data Engineer, Analytics Engineer, Big Data Engineer |
| 3 | **Applied AI & Intelligent Systems** | AI Engineer, ML Engineer, Computer Vision Engineer |
| 4 | **MLOps & Production ML** | MLOps Engineer, ML Platform Engineer, ML Reliability Engineer |
| 5 | **LLM Systems & Applied GenAI** | LLM Engineer, GenAI Engineer, AI Product Engineer, Prompt Engineer |
| 6 | **Cloud-Native & Platform Engineering** | Cloud Engineer, DevOps Engineer, SRE, Platform Engineer |

**Rule:** Pick the segment that matches the role you would actually apply to in placement season. Not the "sexiest" one. Not your friend's choice. Yours.

---

## 3. The Problem Statements (Pick ONE within your segment)

You will find the full catalogue — with detailed business scenarios, scope, and tech direction — in **Document 02: Technical & Business Problem Compendium**.

Quick map of what's on the menu:

**Segment 1 — Insights & Decision Intelligence**
- A1. Churn Radar (SaaS customer churn analytics)
- A2. Pricing Forensics (quick-commerce pricing intelligence)
- A3. Funnel Autopsy (fintech marketing attribution)
- A4. People Analytics (IT services workforce attrition)

**Segment 2 — Data Platform & Pipeline Engineering**
- B1. Unified Commerce Lakehouse (medallion architecture)
- B2. Clickstream Telemetry Pipeline (real-time event processing)
- B3. Regulatory Data Mesh (BFSI multi-domain)
- B4. CDC Replicator (change-data-capture from OLTP)

**Segment 3 — Applied AI & Intelligent Systems**
- C1. Contract Intelligence (RAG over legal/HR contracts)
- C2. Visual Quality Inspection (manufacturing defect detection)
- C3. Voice-First Customer Support (multilingual speech AI)
- C4. Predictive Supply Chain (FMCG demand forecasting)

**Segment 4 — MLOps & Production ML**
- D1. Feature Store in a Box (Feast/Hopsworks platform)
- D2. Continuous Training Platform (drift-triggered retraining)
- D3. LLMOps Control Plane (prompt + provider governance)
- D4. Model Risk & Governance (regulated-industry ML audit)

**Segment 5 — LLM Systems & Applied GenAI**
- E1. Agentic Research Analyst (multi-agent equity research)
- E2. Domain Copilot (vertical assistant with tool-use)
- E3. RAG over Enterprise Mess (multi-modal dirty data)
- E4. Fine-Tuned Specialist Model (QLoRA on a niche domain)

**Segment 6 — Cloud-Native & Platform Engineering**
- F1. Multi-Tenant SaaS Backbone (tenant isolation + billing)
- F2. Event-Driven Order System (saga on k8s)
- F3. Cost-Optimised Data Lake on a Shoestring (<₹500/month)
- F4. GitOps Reference Platform (ArgoCD + sealed-secrets + observability)

---

## 4. The 5-Week Workflow

### Week 0 (Before 22 June) — Pre-Internship Prep
- Read this workflow guide end to end.
- Skim the Technical & Business Problem Compendium.
- Identify your **top 2 segments** and **top 3 problem statements**.
- Set up your tooling: GitHub account (clean profile), Python 3.11+, Docker, a free-tier cloud account, a code editor of your choice.
- Join the cohort Slack/Discord.

### Day 1 (22 June, Mon) — Segment Orientation
- Morning: Welcome + segment overviews by mentors (1 mentor per segment).
- Afternoon: Self-assessment form (skills, interests, target companies) → submit your **Segment Ranker**.
- Evening: Problem-statement teaser decks released.

### Day 2 (23 June, Tue) — Problem Deep-Dive
- Per-segment deep-dives on each problem statement (scenario, scope, tech direction, eval criteria).
- Talk to mentors. Read the Compendium entries for your shortlist.

### Day 3 (24 June, Wed) — Lock Your Choice
- Submit final segment + problem statement.
- Submit your **Initial Design Doc (1 page)** by 11:59 PM. Template provided.

### Day 4-5 (25-26 June, Thu-Fri) — Architecture Review
- 30-min 1:1 with your segment mentor. Walk through your design doc.
- Incorporate feedback, lock the architecture.
- **Friday EOD:** Final architecture + tech-stack sign-off.

### Week 1 (29 Jun – 3 Jul) — Foundation Sprint
**Theme:** Data + scaffolding.
- Set up the repo, CI, environments, data sources.
- Stand up the data layer (ingestion, warehouse, feature store — whatever applies).
- **Friday Demo #1:** Working data layer + first notebook/script run end-to-end on a small slice of the problem.

### Week 2 (6 Jul – 10 Jul) — Core Build Sprint
**Theme:** The "happy path" of the product works.
- Implement the core model/pipeline/dashboard/agent.
- First end-to-end run on the full dataset.
- **Friday Demo #2:** End-to-end "skinny" version of the product works. Ugly UI is fine. Functionality is not.

### Week 3 (13 Jul – 17 Jul) — Hardening Sprint
**Theme:** Tests, observability, edge cases, the boring stuff that wins interviews.
- Add tests (unit + integration + data quality).
- Add monitoring/logging/tracing.
- Add a README that someone outside LPU could read and run your project.
- **Friday Demo #3:** "If a recruiter cloned this repo right now, it would work in 15 minutes."

### Week 4 (20 Jul – 24 Jul) — Production Polish Sprint
**Theme:** Ship it.
- Deploy to a real environment (free tier is fine).
- Write the architecture decision records (ADRs).
- Record a 5-min Loom walkthrough.
- Update resume with this project (3-4 bullets).
- **Friday Demo #4:** Live deployment, live walkthrough, live Q&A.

### Week 5 (25-26 Jul) — Final Submission & Showcase
- **25 Jul (Sat):** Final submission (repo, deployed URL, all docs, Loom, resume bullets). Internal eval.
- **26 Jul (Sun):** Public showcase. Top 6 projects (1 per segment) present to a panel. Certificates issued per segment.

---

## 5. The 3-Artifact Rule

Every student ships exactly **3 artifacts** by 26 July:

| # | Artifact | Purpose |
|---|----------|---------|
| 1 | **The Hero Project** | The production-grade project tied to your chosen problem statement. This is what goes on the top line of your resume. |
| 2 | **The Thinking Artifact** | A 1 written piece — could be a PRD, ADR set, postmortem, design deep-dive, or research note. Shows you can write and think. |
| 3 | **The Presence Artifact** | Either a public blog post (1500+ words) OR a 5-min Loom walkthrough OR a public talk/lightning demo. Gets you visible. |

The details of WHAT each of these is for your specific problem statement are in **Document 02**.

---

## 6. Weekly Cadence (The Rhythm)

Every week looks like this. Non-negotiable.

| Day | Activity |
|-----|----------|
| Monday | Sprint planning: write 3-5 tasks for the week in a GitHub Project board. |
| Tue–Thu | Build. Commit often. Push daily. |
| Friday | Demo day. 5-min live walkthrough to your segment mentor + 2 peers. Record it. |
| Saturday | Write: blog post, ADR, postmortem, README polish. |
| Sunday | Off. Rest. Read. Catch up on gaps. |

**Push code every day.** Even a small commit. A green commit graph in your GitHub profile is itself a presence artifact.

---

## 7. What "Production-Grade" Means Here

You will hear this phrase 100 times this month. Here's the working definition:

A production-grade project has:
- ✅ Code in Git, with a clean commit history
- ✅ README that explains the why, what, how, and how-to-run in <10 minutes
- ✅ Automated tests (at least the critical paths)
- ✅ Logging + error handling (no `try: ... except: pass`)
- ✅ A deployed, live URL (even if it's a free-tier VM)
- ✅ A 5-min Loom showing it working
- ✅ At least 3 "ADRs" — small markdown files explaining key technical decisions

It does NOT need to handle 10,000 users. It needs to look like you know how to build something that *could*.

---

## 8. Help & Escalation

| Need | Where to go |
|------|-------------|
| Stuck on a concept | Segment mentor office hours (Wed + Fri, 4-5 PM) |
| Stuck on a build issue | Cohort Slack #help channel |
| Personal blocker (health, time, life) | Internship coordinator — no judgement |
| Disagreement with mentor on scope | Raise to internship lead, expect a 24-hr turnaround |
| Want to switch problem statement | Allowed only in Week 1, with mentor sign-off |

---

## 9. What's NOT Allowed

- ❌ Group projects of any size
- ❌ Submitting work done before 22 June 2026
- ❌ Submitting a closed-source project (everything must be on your public GitHub)
- ❌ "I couldn't deploy it" — there is a free tier for every cloud; you can deploy
- ❌ Skipping the writing artifacts — recruiters will Google you
- ❌ Going silent. If you're stuck, say so in the #help channel within 24 hours of being stuck

---

## 10. The Final Eval

You will be evaluated on **4 dimensions**, each equally weighted:

1. **Technical Depth (25%)** — Does the code work? Is the architecture sound? Are the tests real?
2. **Product Sense (25%)** — Did you solve a real business problem or just a tutorial problem? Does the UX make sense?
3. **Engineering Hygiene (25%)** — Repo, README, tests, ADRs, deploy, observability.
4. **Communication (25%)** — Loom, blog post, demo ability, writing quality, resume bullets.

A mediocre project with great communication will outscore a brilliant project with no writeup. Don't skip the writing.

---

## 11. Documents in This Series

| Doc | Purpose |
|-----|---------|
| **01 — Workflow Guide (this doc)** | What to do, when, how. Process. |
| **02 — Technical & Business Problem Compendium** | The detailed scenario, scope, and tech direction for every problem statement. |
| **03 — Deliverables Specification** | The exact weekly + milestone deliverables. What, when, format, evaluation. |

Read 01 fully before 22 June. Start skimming 02 by 20 June. Read 03 fully by 24 June.

---

**One last thing.** 5 weeks is short. You will be tempted to spend 3 weeks "researching." Don't. Pick a direction by Day 3. The research happens in the building. The internship is a build sprint, not a literature review.

See you on 22 June.
