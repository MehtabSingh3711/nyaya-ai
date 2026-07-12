from __future__ import annotations

import re
import uuid
from nyaya_ai.contracts.extractor import ExtractedContract
from nyaya_ai.schemas import ClauseExtraction

# Pattern to find clause headers at the start of a line.
# Matches: "1. Scope", "Clause 2.1: Payment", "Section 3. Liability"
# Number format: 1, 1.1, 2.3.4, etc.
# CRITICAL: re.MULTILINE is used so ^ matches start of any line.
CLAUSE_PATTERN = re.compile(
    r"^(?:Clause|Section)?[ \t]*(\d+(?:\.\d+)*)(?:\.|\:)?[ \t]+",
    re.MULTILINE | re.IGNORECASE,
)


def chunk_contract(extraction: ExtractedContract) -> list[ClauseExtraction]:
    """Split the extracted contract text into structural clauses.

    Determines page number where the clause starts (for PDF) or defaults
    to 0 (for DOCX). Falls back to paragraph-level splitting if no
    structural numbering is detected.

    Args:
        extraction: The ExtractedContract result.

    Returns:
        List of ClauseExtraction objects with clause_type='other'.
    """
    contract_id = str(uuid.uuid4())
    contract_name = extraction.contract_name

    # 1. Rebuild full text and map character offsets to pages
    full_text = ""
    page_offsets = []

    if extraction.pages:
        for page in extraction.pages:
            start_offset = len(full_text)
            full_text += page.text + "\n"
            page_offsets.append((page.page_number, start_offset))
    else:
        full_text = "\n\n".join(extraction.paragraphs)
        page_offsets.append((0, 0))

    def get_page_number(char_idx: int) -> int:
        current_page = 0
        for page_num, offset in page_offsets:
            if char_idx >= offset:
                current_page = page_num
            else:
                break
        return current_page

    # 2. Find all clause boundaries
    matches = list(CLAUSE_PATTERN.finditer(full_text))

    clauses: list[ClauseExtraction] = []

    if not matches:
        # Fallback to paragraph splitting if no clause numbers detected
        paragraphs = [p.strip() for p in full_text.split("\n\n") if p.strip()]
        for i, p in enumerate(paragraphs, 1):
            idx = full_text.find(p)
            page_num = get_page_number(idx if idx != -1 else 0)
            clauses.append(
                ClauseExtraction(
                    contract_id=contract_id,
                    contract_name=contract_name,
                    clause_number=str(i),
                    clause_text=p,
                    page=page_num,
                    clause_type="other",
                )
            )
        return clauses

    # 3. Slice the text based on matches
    for i, match in enumerate(matches):
        clause_num = match.group(1)
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)

        clause_text = full_text[start:end].strip()
        if not clause_text:
            continue

        page_num = get_page_number(start)

        clauses.append(
            ClauseExtraction(
                contract_id=contract_id,
                contract_name=contract_name,
                clause_number=clause_num,
                clause_text=clause_text,
                page=page_num,
                clause_type="other",
            )
        )

    return clauses
