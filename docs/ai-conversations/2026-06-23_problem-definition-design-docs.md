# AI Session Log — 2026-06-23 — Problem Definition + Design Docs

**Agent:** Antigravity (Claude Sonnet 4.6 — Thinking)
**Phase:** Week 1 — Foundation
**Session opened:** 11:52 IST

## Session Goal

Produce three mentor-ready documents by Friday 26 June:
1. `/docs/problem-statement.md` — formal 6-section problem statement
2. `/docs/initial-design-doc.md` — 1-page design doc (due 24 June)
3. `/docs/architecture.md` — full architecture + tech stack (due 26 June)

## Decisions Log

### Discovery Answers — Problem Statement
**Logged at:** 2026-06-23, 12:00 IST

**Q1 — Hero user:** Anyone in India who has received a contract they don't fully understand and cannot afford a lawyer to review it.

**Q2 — Most painful moment:** They sign a contract with an exploitative or legally void clause buried in legal jargon — a non-compete under ICA §27, a payment term violating the MSME Act, an uncapped liability clause — and only discover the consequence after it's too late.

**Q3 — Hero feature:** F1 — ICA §27 non-compete detector. Most dramatic, universally relatable, zero context needed in a 60-second demo.

**Q4 — Target companies:** SpotDraft (Indian legal-tech, exact domain), Sarvam AI (Indian AI lab, domain-specific RAG), Razorpay (MSME-serving product company with strong AI team).

**Q5 — Out of scope:** Criminal law analysis and court judgment research — planned as the next module on the same platform.

---

### Discovery Answers — Initial Design Doc
**Logged at:** 2026-06-24, 13:30 IST

**Q1 — Headline idea:** Nyaya AI gives anyone in India the same contract review a ₹50,000 lawyer would give them — in 30 seconds, for free.

**Q2 — Biggest technical risk:** LLM hallucinating legal citations — confidently stating a clause violates ICA §27 or the MSME Act when the retrieved context doesn't support it. Mitigation: cite-or-refuse logic — if retrieved evidence is below confidence threshold, system says "I don't know" rather than generating an unsupported legal claim.

**Q3 — End of Week 1 demo:** Mode 2 first — the legal corpus (ICA 1872, MSME Act 2006, IT Act 2000, IPC 1860) fully ingested and a working RAG agent answering plain-language legal questions with citations. Demo question: "Is a non-compete clause enforceable in India?" — answer cites ICA §27, section number, plain-language explanation. Mode 1 built in Week 2 on top of same infrastructure.

## Code / Output Produced

*(links to commits or key files will be logged here)*

## What the Student Built / Decided

*(filled at end of session)*

## Open Questions for Next Session

*(filled at end of session)*

## Next Session Goal

*(filled at end of session)*

---

## Summary

*(filled at end of session)*
