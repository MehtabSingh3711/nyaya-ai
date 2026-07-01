"""Cross-dataset deduplication for statutory corpus ingestion.

Uses a normalized (act_title, section_number) key to detect and skip
duplicate sections that appear across multiple HuggingFace datasets.

Usage:
    registry = DedupRegistry()
    for chunk in chunks:
        if not registry.is_duplicate(chunk):
            registry.register(chunk)
            # proceed with embedding and indexing
"""

from __future__ import annotations

from nyaya_ai.schemas import CorpusChunk


class DedupRegistry:
    """Tracks seen (act_title, section) pairs to prevent duplicate indexing.

    The registry uses CorpusChunk.dedup_key which normalizes titles by:
    - Lowercasing
    - Stripping leading "the "
    - Stripping trailing 4-digit year
    - Collapsing whitespace
    """

    def __init__(self) -> None:
        self._seen: set[tuple[str, str]] = set()

    def is_duplicate(self, chunk: CorpusChunk) -> bool:
        """Check if this chunk's (act, section) pair has already been seen."""
        return chunk.dedup_key in self._seen

    def register(self, chunk: CorpusChunk) -> None:
        """Register this chunk's (act, section) pair as seen."""
        self._seen.add(chunk.dedup_key)

    def register_and_check(self, chunk: CorpusChunk) -> bool:
        """Check if duplicate, and if not, register it. Returns True if NEW."""
        if self.is_duplicate(chunk):
            return False
        self.register(chunk)
        return True

    @property
    def count(self) -> int:
        """Number of unique (act, section) pairs registered."""
        return len(self._seen)

    def stats(self) -> dict[str, int]:
        """Return registry statistics."""
        return {"unique_sections": self.count}
