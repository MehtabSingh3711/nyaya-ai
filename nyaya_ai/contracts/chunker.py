from __future__ import annotations

import re
import uuid
from nyaya_ai.contracts.extractor import ExtractedContract
from nyaya_ai.schemas import ClauseExtraction

# Heuristic Legal Keywords for detecting unnumbered standalone titles
LEGAL_KEYWORDS = {
    "CONFIDENTIAL", "PAYMENT", "TERM", "LIABILITY", "INDEMNITY", 
    "ARBITRATION", "JURISDICTION", "GOVERNING", "INTELLECTUAL", "IP", 
    "WARRANTY", "DELIVERY", "MISCELLANEOUS", "DEFINITION", "REPRESENTATION", 
    "FORCE MAJEURE", "BREACH", "SEVERABILITY", "NOTICE", "WAIVER", "SURVIVAL",
    "SCOPE", "QUALITY", "TITLE", "SIGNATURE", "WITNESS"
}

# Regex to match numbered boundaries: "1. Scope", "Clause 2.1: Payment", "§ 2.3 Non-Compete", etc.
NUMBERED_PATTERN = re.compile(
    r"^(?:Clause|Section|Article|§)?[ \t]*(\d+(?:\.\d+)*)(?:\.|\:)?[ \t]+",
    re.IGNORECASE
)


def chunk_contract(extraction: ExtractedContract) -> list[ClauseExtraction]:
    """Split the extracted contract text into structural clauses.

    Combines two strategies:
    1. Numbered pattern match (Clause X, Section Y, § Z, Article W, or raw numbers).
    2. Standalone uppercase legal headers (e.g. "CONFIDENTIALITY").

    Falls back to paragraph-level splitting if no headers are detected.

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

    # 2. Scan line-by-line to identify boundaries
    boundaries: list[tuple[int, str]] = []  # (char_offset, clause_number)
    
    current_offset = 0
    lines = full_text.splitlines(keepends=True)

    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            current_offset += len(line)
            continue

        is_boundary = False
        clause_num = None

        # Check 1: Numbered legal header
        regex_match = NUMBERED_PATTERN.match(line_stripped)
        if regex_match:
            is_boundary = True
            clause_num = regex_match.group(1)
        
        # Check 2: Standalone uppercase legal header heuristic
        elif (
            len(line_stripped) < 60 
            and line_stripped.isupper() 
            and any(kw in line_stripped for kw in LEGAL_KEYWORDS)
            and not line_stripped.endswith((".", ",", ";"))
        ):
            is_boundary = True
            clause_num = line_stripped.title()

        if is_boundary:
            boundaries.append((current_offset, clause_num))

        current_offset += len(line)

    # 3. Fallback to paragraph splitting if no boundaries detected
    if not boundaries:
        paragraphs = [p.strip() for p in full_text.split("\n\n") if p.strip()]
        clauses: list[ClauseExtraction] = []
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

    # 4. Slice the text based on boundaries
    clauses: list[ClauseExtraction] = []
    for i, (start, clause_num) in enumerate(boundaries):
        end = boundaries[i + 1][0] if i + 1 < len(boundaries) else len(full_text)
        
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
