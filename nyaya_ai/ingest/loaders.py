"""HuggingFace dataset loaders for Indian legal corpus ingestion.

Loads from two primary sources:
1. mratanusarkar/Indian-Laws — pre-sectioned (act_title, section, law)
2. geekyrakshit/indian-legal-acts — raw Act text (needs chunking)
3. Sahi19/IndianLawComplete — optional, skipped gracefully if unavailable

Returns CorpusChunk objects ready for embedding and indexing.
"""

from __future__ import annotations

from typing import Optional

from rich.console import Console

from nyaya_ai.config import HF_DATASETS, CORPUS_VERSION
from nyaya_ai.ingest.chunker import chunk_pre_sectioned, chunk_raw_act_text
from nyaya_ai.ingest.dedup import DedupRegistry
from nyaya_ai.schemas import CorpusChunk

console = Console()


def load_mratanusarkar(
    registry: DedupRegistry,
) -> list[CorpusChunk]:
    """Load mratanusarkar/Indian-Laws — the primary, pre-sectioned dataset.

    Columns: act_title, section, law
    Each row is already one section. We wrap into CorpusChunk and register
    in the dedup registry.

    Returns:
        List of CorpusChunk objects.
    """
    from datasets import load_dataset

    dataset_id = HF_DATASETS["primary"]
    console.print(f"[bold blue]Loading {dataset_id}...[/]")

    try:
        ds = load_dataset(dataset_id, split="train")
    except Exception as e:
        console.print(f"[red]Failed to load {dataset_id}: {e}[/]")
        return []

    console.print(f"  Rows: {len(ds)}")

    chunks: list[CorpusChunk] = []
    skipped_empty = 0
    skipped_dup = 0

    for row in ds:
        act_title = row.get("act_title", "") or ""
        section = row.get("section", "") or ""
        law_text = row.get("law", "") or ""

        if not act_title.strip() or not law_text.strip():
            skipped_empty += 1
            continue

        chunk = chunk_pre_sectioned(
            act_title=act_title,
            section=section,
            law_text=law_text,
            source=dataset_id,
        )

        if chunk is None:
            skipped_empty += 1
            continue

        if not registry.register_and_check(chunk):
            skipped_dup += 1
            continue

        chunks.append(chunk)

    console.print(
        f"  [green]Loaded: {len(chunks)} sections[/] | "
        f"Empty: {skipped_empty} | Duplicates: {skipped_dup}"
    )
    return chunks


def load_geekyrakshit(
    registry: DedupRegistry,
) -> list[CorpusChunk]:
    """Load geekyrakshit/indian-legal-acts — raw Act texts.

    Each row is a full Act text. We chunk it into sections using the
    structural chunker, then dedup against the registry.

    Returns:
        List of CorpusChunk objects (new ones only, dupes skipped).
    """
    from datasets import load_dataset

    dataset_id = HF_DATASETS["secondary"]
    console.print(f"[bold blue]Loading {dataset_id}...[/]")

    try:
        ds = load_dataset(dataset_id, split="train")
    except Exception as e:
        console.print(f"[red]Failed to load {dataset_id}: {e}[/]")
        return []

    console.print(f"  Documents: {len(ds)}")

    chunks: list[CorpusChunk] = []
    skipped_dup = 0
    total_sections = 0

    for row in ds:
        # Dataset has a 'text' field containing the full Act
        raw_text = row.get("text", "") or ""
        if not raw_text.strip():
            continue

        # Try to extract Act name from the first line
        act_name = _extract_act_name(raw_text)

        # Chunk the raw text into sections
        act_chunks = chunk_raw_act_text(
            raw_text=raw_text,
            act_name=act_name,
            source=dataset_id,
        )

        total_sections += len(act_chunks)

        for chunk in act_chunks:
            if not registry.register_and_check(chunk):
                skipped_dup += 1
                continue
            chunks.append(chunk)

    console.print(
        f"  [green]Loaded: {len(chunks)} new sections[/] | "
        f"Total parsed: {total_sections} | Duplicates: {skipped_dup}"
    )
    return chunks


def load_sahi19(
    registry: DedupRegistry,
) -> list[CorpusChunk]:
    """Load Sahi19/IndianLawComplete — optional dataset.

    Gracefully skips if the dataset doesn't exist or fails to load.
    """
    from datasets import load_dataset

    dataset_id = HF_DATASETS["optional"]
    console.print(f"[bold blue]Trying {dataset_id} (optional)...[/]")

    try:
        ds = load_dataset(dataset_id, split="train")
    except Exception as e:
        console.print(f"  [yellow]Skipped: {e}[/]")
        return []

    console.print(f"  Rows: {len(ds)}")

    # Inspect columns to determine structure
    columns = ds.column_names
    console.print(f"  Columns: {columns}")

    chunks: list[CorpusChunk] = []
    skipped_dup = 0

    # Try to adapt to whatever columns exist
    for row in ds:
        act_title = (
            row.get("act_title")
            or row.get("title")
            or row.get("act_name")
            or "Unknown Act"
        )
        section = (
            row.get("section")
            or row.get("section_number")
            or "0"
        )
        text = (
            row.get("law")
            or row.get("text")
            or row.get("content")
            or ""
        )

        if not text.strip():
            continue

        chunk = chunk_pre_sectioned(
            act_title=str(act_title),
            section=str(section),
            law_text=str(text),
            source=dataset_id,
        )

        if chunk is None:
            continue

        if not registry.register_and_check(chunk):
            skipped_dup += 1
            continue

        chunks.append(chunk)

    console.print(
        f"  [green]Loaded: {len(chunks)} sections[/] | Duplicates: {skipped_dup}"
    )
    return chunks


def _extract_act_name(raw_text: str) -> str:
    """Extract Act name from the first line(s) of raw Act text.

    Heuristic: the first non-empty line that looks like a title
    (contains "ACT" or has a year pattern).
    """
    for line in raw_text.split("\n")[:10]:
        line = line.strip()
        if not line:
            continue
        # Common patterns: "THE INDIAN CONTRACT ACT, 1872" or similar
        if "ACT" in line.upper() or "CODE" in line.upper():
            # Clean up: remove "THE " prefix, trailing punctuation
            name = line.strip().rstrip(".")
            return name
        # If line has a 4-digit year, likely a title
        if any(c.isdigit() for c in line) and len(line) > 10:
            return line.strip().rstrip(".")

    # Fallback: first non-empty line
    for line in raw_text.split("\n"):
        line = line.strip()
        if line:
            return line[:100]  # cap at 100 chars

    return "Unknown Act"


def load_gsms_b(registry: DedupRegistry) -> list[CorpusChunk]:
    """Load GSMS-B/indian-legal-sections-bns-bnss-bsa-2023.

    Contains 1,059 verified sections from the new 2023 criminal justice reform acts:
    Bharatiya Nyaya Sanhita (BNS), Bharatiya Nagarik Suraksha Sanhita (BNSS),
    and Bharatiya Sakshya Adhiniyam (BSA).
    """
    from datasets import load_dataset

    dataset_id = "GSMS-B/indian-legal-sections-bns-bnss-bsa-2023"
    console.print(f"[bold blue]Loading {dataset_id}...[/]")

    try:
        ds = load_dataset(dataset_id, split="train")
    except Exception as e:
        console.print(f"[red]Failed to load {dataset_id}: {e}[/]")
        return []

    console.print(f"  Rows: {len(ds)}")

    chunks: list[CorpusChunk] = []
    skipped_dup = 0
    skipped_empty = 0

    for row in ds:
        # Actual keys in GSMS-B: act, section_number, text, section_title, chapter
        act_title = row.get("act", "") or ""
        section = row.get("section_number", "") or ""
        law_text = row.get("text", "") or ""
        section_title = row.get("section_title", "") or None
        chapter = row.get("chapter", "") or None

        if not act_title.strip() or not law_text.strip():
            skipped_empty += 1
            continue

        chunk = CorpusChunk(
            act_name=act_title.strip(),
            section_number=str(section).strip(),
            section_title=section_title.strip() if section_title else None,
            chapter=chapter.strip() if chapter else None,
            text=law_text.strip(),
            source=dataset_id,
            version="2023-reforms",
        )

        if not registry.register_and_check(chunk):
            skipped_dup += 1
            continue

        chunks.append(chunk)

    console.print(
        f"  [green]Loaded: {len(chunks)} sections[/] | "
        f"Empty: {skipped_empty} | Duplicates: {skipped_dup}"
    )
    return chunks

