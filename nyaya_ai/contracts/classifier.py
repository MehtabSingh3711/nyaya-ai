from __future__ import annotations

import re

# Keywords for local classification
KEYWORDS = {
    "non_compete": [
        "non-compete",
        "noncompete",
        "non-solicit",
        "nonsolicit",
        "restrictive covenant",
        "restraint of trade",
        "exclusivity",
        "not compete",
        "not solicit",
        "post-termination restraint",
    ],
    "payment_term": [
        "payment",
        "invoice",
        "fees",
        "remuneration",
        "pricing",
        "rate",
        "due date",
        "billing",
        "days of receipt",
        "interest",
        "late payment",
    ],
    "termination": [
        "termination",
        "terminate",
        "expiry",
        "expire",
        "survival",
        "cure period",
        "material breach",
        "without cause",
        "written notice",
        "renew",
    ],
    "liability": [
        "liability",
        "limitation of liability",
        "consequential damages",
        "indirect loss",
        "maximum liability",
        "aggregate liability",
        "exclusion of damages",
    ],
    "IP": [
        "intellectual property",
        "copyright",
        "patent",
        "trademark",
        "ownership",
        "work product",
        "invention",
        "proprietary",
        "license grant",
        "assignee",
    ],
    "indemnity": [
        "indemnify",
        "indemnification",
        "hold harmless",
        "defend",
        "losses",
        "damages",
        "claims",
        "costs",
    ],
    "arbitration": [
        "arbitration",
        "governing law",
        "jurisdiction",
        "dispute resolution",
        "arbitrator",
        "tribunal",
        "venue",
        "courts of",
    ],
    "penalty": [
        "penalty",
        "liquidated damages",
        "penalty clause",
        "forfeit",
        "forfeiture",
        "penal",
        "pre-determined damages",
        "predetermined damages",
    ],
}


def classify_clause(clause_text: str) -> tuple[str, str | None]:
    """Perform keyword-based best-guess classification of a clause.

    Args:
        clause_text: The verbatim text of the contract clause.

    Returns:
        A tuple of (clause_type, clause_type_detail).
        clause_type is one of: payment_term, termination, liability, IP,
        non_compete, indemnity, arbitration, other.
    """
    text = clause_text.lower()
    scores = {}

    for clause_type, kw_list in KEYWORDS.items():
        score = 0
        for kw in kw_list:
            score += text.count(kw)
        if score > 0:
            scores[clause_type] = score

    if not scores:
        return "other", None

    # Find the type with the highest score
    best_type = max(scores, key=scores.get)

    # Extract best guess details using simple regexes
    detail = None
    if best_type == "payment_term":
        days_match = re.search(r"\b\d+\s+days?\b", text)
        if days_match:
            detail = f"Payment term: {days_match.group(0)}"
    elif best_type == "non_compete":
        duration_match = re.search(r"\b\d+\s+(?:years?|months?)\b", text)
        if duration_match:
            detail = f"Non-compete duration: {duration_match.group(0)}"
    elif best_type == "termination":
        notice_match = re.search(r"\b\d+\s+days?\s+notice\b", text)
        if notice_match:
            detail = f"Termination notice: {notice_match.group(0)}"

    return best_type, detail
