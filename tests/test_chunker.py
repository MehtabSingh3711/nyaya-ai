"""Tests for nyaya_ai.ingest.chunker — structural section-level chunking."""

import pytest

from nyaya_ai.ingest.chunker import (
    chunk_pre_sectioned,
    chunk_raw_act_text,
    _estimate_tokens,
)


# ===================================================================
# chunk_pre_sectioned tests
# ===================================================================

class TestChunkPreSectioned:
    """Pre-sectioned data → CorpusChunk."""

    def test_basic_row(self):
        chunk = chunk_pre_sectioned(
            act_title="Indian Contract Act 1872",
            section="Section 27 - Agreements in restraint of trade void",
            law_text="Every agreement by which any one is restrained from "
                     "exercising a lawful profession, trade or business of "
                     "any kind, is to that extent void.",
            source="test",
        )
        assert chunk is not None
        assert chunk.act_name == "Indian Contract Act 1872"
        assert chunk.section_number == "27"
        assert chunk.section_title == "Agreements in restraint of trade void"

    def test_section_number_only(self):
        chunk = chunk_pre_sectioned(
            act_title="ICA 1872",
            section="27",
            law_text="Some legal text.",
            source="test",
        )
        assert chunk is not None
        assert chunk.section_number == "27"

    def test_empty_text_returns_none(self):
        chunk = chunk_pre_sectioned(
            act_title="ICA 1872",
            section="27",
            law_text="",
            source="test",
        )
        assert chunk is None

    def test_whitespace_only_returns_none(self):
        chunk = chunk_pre_sectioned(
            act_title="ICA 1872",
            section="27",
            law_text="   \n  \t  ",
            source="test",
        )
        assert chunk is None

    def test_strips_whitespace(self):
        chunk = chunk_pre_sectioned(
            act_title="  ICA 1872  ",
            section="  27  ",
            law_text="  Some text.  ",
            source="test",
        )
        assert chunk is not None
        assert chunk.act_name == "ICA 1872"
        assert chunk.text == "Some text."


# ===================================================================
# chunk_raw_act_text tests
# ===================================================================

class TestChunkRawActText:
    """Raw Act text → list of CorpusChunks."""

    SAMPLE_ACT = """THE INDIAN CONTRACT ACT, 1872

CHAPTER II

1. Short title.—This Act may be called the Indian Contract Act, 1872. It extends to the whole of India except the State of Jammu and Kashmir.

2. Interpretation-clause.—In this Act the following words and expressions are used in the following senses, unless a contrary intention appears from the context.

27. Agreements in restraint of trade void.—Every agreement by which any one is restrained from exercising a lawful profession, trade or business of any kind, is to that extent void.

28. Agreements in restraint of legal proceedings void.—Every agreement, by which any party thereto is restricted absolutely from enforcing his rights under or in respect of any contract, by the usual legal proceedings in the ordinary tribunals, is void.
"""

    def test_detects_sections(self):
        chunks = chunk_raw_act_text(
            self.SAMPLE_ACT,
            act_name="Indian Contract Act 1872",
            source="test",
        )
        assert len(chunks) >= 3  # sections 1, 2, 27, 28
        section_numbers = [c.section_number for c in chunks]
        assert "27" in section_numbers
        assert "28" in section_numbers

    def test_preserves_act_name(self):
        chunks = chunk_raw_act_text(
            self.SAMPLE_ACT,
            act_name="Indian Contract Act 1872",
            source="test",
        )
        for chunk in chunks:
            assert chunk.act_name == "Indian Contract Act 1872"

    def test_preserves_source(self):
        chunks = chunk_raw_act_text(
            self.SAMPLE_ACT,
            act_name="ICA",
            source="geekyrakshit/indian-legal-acts",
        )
        for chunk in chunks:
            assert chunk.source == "geekyrakshit/indian-legal-acts"

    def test_empty_text_returns_empty(self):
        assert chunk_raw_act_text("", act_name="Test", source="test") == []

    def test_whitespace_only_returns_empty(self):
        assert chunk_raw_act_text("   \n  ", act_name="Test", source="test") == []

    def test_no_sections_returns_single_chunk(self):
        """Text without any section markers → one chunk with full text."""
        text = "This is a preamble without any numbered sections. " * 20
        chunks = chunk_raw_act_text(text, act_name="Test Act", source="test")
        # Should return 1 chunk (whole text) since no sections detected
        assert len(chunks) == 1
        assert chunks[0].section_number == "0"

    def test_section_text_includes_content(self):
        chunks = chunk_raw_act_text(
            self.SAMPLE_ACT,
            act_name="ICA 1872",
            source="test",
        )
        sec_27 = [c for c in chunks if c.section_number == "27"]
        assert len(sec_27) == 1
        assert "restrained" in sec_27[0].text


# ===================================================================
# Token estimation
# ===================================================================

class TestEstimateTokens:
    def test_empty(self):
        assert _estimate_tokens("") == 0

    def test_approximate(self):
        # ~4 chars per token
        text = "a" * 400
        assert _estimate_tokens(text) == 100
