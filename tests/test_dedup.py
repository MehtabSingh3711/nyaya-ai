"""Tests for nyaya_ai.ingest.dedup — cross-dataset deduplication."""

import pytest

from nyaya_ai.ingest.dedup import DedupRegistry
from nyaya_ai.schemas import CorpusChunk


def _make_chunk(act_name: str, section: str, source: str = "test") -> CorpusChunk:
    """Helper to create a minimal CorpusChunk for testing."""
    return CorpusChunk(
        act_name=act_name,
        section_number=section,
        text="Some legal text content here.",
        source=source,
    )


class TestDedupRegistry:
    """DedupRegistry — tracks seen (act, section) pairs."""

    def test_new_chunk_is_not_duplicate(self):
        reg = DedupRegistry()
        chunk = _make_chunk("Indian Contract Act 1872", "27")
        assert not reg.is_duplicate(chunk)

    def test_registered_chunk_is_duplicate(self):
        reg = DedupRegistry()
        chunk = _make_chunk("Indian Contract Act 1872", "27")
        reg.register(chunk)
        assert reg.is_duplicate(chunk)

    def test_register_and_check_returns_true_for_new(self):
        reg = DedupRegistry()
        chunk = _make_chunk("ICA 1872", "27")
        assert reg.register_and_check(chunk) is True

    def test_register_and_check_returns_false_for_dup(self):
        reg = DedupRegistry()
        chunk = _make_chunk("ICA 1872", "27")
        reg.register_and_check(chunk)
        assert reg.register_and_check(chunk) is False

    def test_different_sections_are_not_duplicates(self):
        reg = DedupRegistry()
        c1 = _make_chunk("Indian Contract Act 1872", "27")
        c2 = _make_chunk("Indian Contract Act 1872", "28")
        reg.register(c1)
        assert not reg.is_duplicate(c2)

    def test_different_acts_are_not_duplicates(self):
        reg = DedupRegistry()
        c1 = _make_chunk("Indian Contract Act 1872", "27")
        c2 = _make_chunk("MSME Development Act 2006", "27")
        reg.register(c1)
        assert not reg.is_duplicate(c2)

    def test_cross_dataset_dedup_with_title_normalization(self):
        """Same Act+section from two datasets with different naming."""
        reg = DedupRegistry()
        c1 = _make_chunk("The Indian Contract Act 1872", "27", source="dataset_a")
        c2 = _make_chunk("Indian Contract Act", "27", source="dataset_b")
        reg.register(c1)
        assert reg.is_duplicate(c2)

    def test_count_tracks_unique_pairs(self):
        reg = DedupRegistry()
        reg.register(_make_chunk("ICA 1872", "27"))
        reg.register(_make_chunk("ICA 1872", "28"))
        reg.register(_make_chunk("MSME Act 2006", "15"))
        assert reg.count == 3

    def test_stats(self):
        reg = DedupRegistry()
        reg.register(_make_chunk("ICA 1872", "27"))
        assert reg.stats() == {"unique_sections": 1}

    def test_empty_registry(self):
        reg = DedupRegistry()
        assert reg.count == 0
        assert reg.stats() == {"unique_sections": 0}
