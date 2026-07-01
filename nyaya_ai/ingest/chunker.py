"""Section-level structural chunker for Indian legal Acts.

Handles two input types:
1. Pre-sectioned data (from mratanusarkar/Indian-Laws) — already split,
   just needs wrapping into CorpusChunk.
2. Raw Act text (from geekyrakshit/indian-legal-acts) — needs regex-based
   section boundary detection and splitting.

ADR-001: Structural chunking primary. LLM fallback deferred to later sprint.
"""

from __future__ import annotations

import re
from typing import Optional

from nyaya_ai.config import MAX_CHUNK_TOKENS, MIN_CHUNK_TOKENS, CORPUS_VERSION
from nyaya_ai.schemas import CorpusChunk


# ---------------------------------------------------------------------------
# Regex patterns for Indian legal Act structure
# ---------------------------------------------------------------------------

# Matches: "27. Agreements in restraint of trade void.—"
# Also: "27A. Special provision..." or "124. Sedition.—"
SECTION_PATTERN = re.compile(
    r"^(\d+[A-Z]?)\.\s+(.+?)(?:[\.\u2014\-]|$)",
    re.MULTILINE,
)

# Matches: "CHAPTER II" or "Chapter IV" or "CHAPTER XIV"
CHAPTER_PATTERN = re.compile(
    r"^(?:CHAPTER|Chapter)\s+([IVXLCDM]+|\d+)(?:\s*[\.\u2014\-]\s*(.*))?",
    re.MULTILINE,
)


def _estimate_tokens(text: str) -> int:
    """Rough token count estimate: ~4 chars per token for English legal text."""
    return len(text) // 4


# ---------------------------------------------------------------------------
# Pre-sectioned data → CorpusChunk
# ---------------------------------------------------------------------------

def chunk_pre_sectioned(
    act_title: str,
    section: str,
    law_text: str,
    source: str,
) -> Optional[CorpusChunk]:
    """Convert a single pre-sectioned row into a CorpusChunk.

    Used for mratanusarkar/Indian-Laws where each row is already one section.
    Returns None if the text is empty or whitespace-only.
    """
    text = law_text.strip()
    if not text:
        return None

    # Try to split section field into number and title
    # e.g. "Section 27 - Agreements in restraint of trade void"
    section_number = section.strip()
    section_title = None

    # Common patterns in the dataset
    sec_match = re.match(
        r"(?:Section\s+)?(\d+[A-Z]?)(?:\s*[\.\-\u2014]\s*(.+))?",
        section_number,
        re.IGNORECASE,
    )
    if sec_match:
        section_number = sec_match.group(1)
        section_title = sec_match.group(2)

    return CorpusChunk(
        act_name=act_title.strip(),
        section_number=section_number,
        section_title=section_title,
        text=text,
        source=source,
        version=CORPUS_VERSION,
    )


# ---------------------------------------------------------------------------
# Raw Act text → list of CorpusChunks
# ---------------------------------------------------------------------------

def chunk_raw_act_text(
    raw_text: str,
    act_name: str,
    source: str,
) -> list[CorpusChunk]:
    """Split a raw Act text into section-level chunks.

    Uses regex to detect section boundaries (e.g. "27. Title.—").
    Tracks current chapter for metadata enrichment.

    Args:
        raw_text: Full text of the Act.
        act_name: Name of the Act (e.g. "Indian Contract Act 1872").
        source: Provenance string (e.g. "geekyrakshit/indian-legal-acts").

    Returns:
        List of CorpusChunk objects, one per detected section.
    """
    if not raw_text or not raw_text.strip():
        return []

    chunks: list[CorpusChunk] = []
    current_chapter: Optional[str] = None

    # Find all section start positions
    section_matches = list(SECTION_PATTERN.finditer(raw_text))

    if not section_matches:
        # No sections detected — return entire text as one chunk
        text = raw_text.strip()
        if text and _estimate_tokens(text) >= MIN_CHUNK_TOKENS:
            chunks.append(
                CorpusChunk(
                    act_name=act_name,
                    section_number="0",
                    section_title="Full text (no sections detected)",
                    text=text,
                    source=source,
                    version=CORPUS_VERSION,
                )
            )
        return chunks

    # Extract sections between boundaries
    for i, match in enumerate(section_matches):
        section_number = match.group(1)
        section_title = match.group(2).strip() if match.group(2) else None

        # Section text runs from this match to the next match (or end of text)
        start = match.start()
        end = section_matches[i + 1].start() if i + 1 < len(section_matches) else len(raw_text)
        section_text = raw_text[start:end].strip()

        # Check for chapter heading before this section
        preceding_text = raw_text[:start]
        chapter_matches = list(CHAPTER_PATTERN.finditer(preceding_text))
        if chapter_matches:
            last_chapter = chapter_matches[-1]
            current_chapter = last_chapter.group(1)

        if not section_text or _estimate_tokens(section_text) < MIN_CHUNK_TOKENS:
            continue

        # Handle long sections: split at sub-section boundaries
        if _estimate_tokens(section_text) > MAX_CHUNK_TOKENS:
            sub_chunks = _split_long_section(
                section_text, section_number, section_title,
                current_chapter, act_name, source,
            )
            chunks.extend(sub_chunks)
        else:
            chunks.append(
                CorpusChunk(
                    act_name=act_name,
                    section_number=section_number,
                    section_title=section_title,
                    chapter=current_chapter,
                    text=section_text,
                    source=source,
                    version=CORPUS_VERSION,
                )
            )

    return chunks


def _split_long_section(
    text: str,
    section_number: str,
    section_title: Optional[str],
    chapter: Optional[str],
    act_name: str,
    source: str,
) -> list[CorpusChunk]:
    """Split a long section into sub-section chunks.

    Looks for sub-section markers like (1), (2), (a), (b).
    Falls back to paragraph splitting if no sub-sections found.
    """
    # Try sub-section splitting: (1), (2), etc.
    subsection_pattern = re.compile(r"\n\s*\((\d+)\)\s")
    sub_matches = list(subsection_pattern.finditer(text))

    if len(sub_matches) >= 2:
        # Split at sub-section boundaries
        chunks = []
        for i, match in enumerate(sub_matches):
            start = match.start()
            end = (
                sub_matches[i + 1].start()
                if i + 1 < len(sub_matches)
                else len(text)
            )
            sub_text = text[start:end].strip()
            if sub_text:
                chunks.append(
                    CorpusChunk(
                        act_name=act_name,
                        section_number=f"{section_number}({match.group(1)})",
                        section_title=section_title,
                        chapter=chapter,
                        text=sub_text,
                        source=source,
                        version=CORPUS_VERSION,
                    )
                )
        # Include any preamble text before the first sub-section
        if sub_matches[0].start() > 0:
            preamble = text[: sub_matches[0].start()].strip()
            if preamble and _estimate_tokens(preamble) >= MIN_CHUNK_TOKENS:
                chunks.insert(
                    0,
                    CorpusChunk(
                        act_name=act_name,
                        section_number=section_number,
                        section_title=section_title,
                        chapter=chapter,
                        text=preamble,
                        source=source,
                        version=CORPUS_VERSION,
                    ),
                )
        return chunks

    # Fallback: return as single chunk even if long
    return [
        CorpusChunk(
            act_name=act_name,
            section_number=section_number,
            section_title=section_title,
            chapter=chapter,
            text=text,
            source=source,
            version=CORPUS_VERSION,
        )
    ]
