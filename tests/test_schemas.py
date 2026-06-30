"""Tests for nyaya_ai.schemas — Pydantic v2 models.

Covers:
- Citation: valid construction, missing fields, empty quote rejection
- CitedAnswer: valid construction, cite-or-refuse validation, confidence bounds
- CorpusChunk: valid construction, dedup_key normalization, payload export
"""

import pytest
from pydantic import ValidationError

from nyaya_ai.schemas import Citation, CitedAnswer, CorpusChunk


# ===================================================================
# Citation tests
# ===================================================================

class TestCitation:
    """Citation model — a single source reference."""

    def test_valid_citation(self):
        c = Citation(
            act_name="Indian Contract Act 1872",
            section="27",
            quote="Every agreement by which any one is restrained from exercising a lawful profession, trade or business of any kind, is to that extent void.",
        )
        assert c.source_type == "statute"
        assert c.act_name == "Indian Contract Act 1872"
        assert c.section == "27"
        assert len(c.quote) > 0

    def test_missing_act_name_raises(self):
        with pytest.raises(ValidationError):
            Citation(section="27", quote="Some quote")

    def test_missing_section_raises(self):
        with pytest.raises(ValidationError):
            Citation(act_name="ICA 1872", quote="Some quote")

    def test_empty_quote_raises(self):
        with pytest.raises(ValidationError):
            Citation(act_name="ICA 1872", section="27", quote="")

    def test_source_type_defaults_to_statute(self):
        c = Citation(act_name="ICA 1872", section="27", quote="text")
        assert c.source_type == "statute"


# ===================================================================
# CitedAnswer tests
# ===================================================================

class TestCitedAnswer:
    """CitedAnswer model — the full structured LLM response."""

    @pytest.fixture
    def valid_citation(self):
        return Citation(
            act_name="Indian Contract Act 1872",
            section="27",
            quote="Every agreement by which any one is restrained...",
        )

    def test_valid_answer_with_citation(self, valid_citation):
        a = CitedAnswer(
            answer="Non-compete clauses are void under ICA §27.",
            citations=[valid_citation],
            confidence=0.92,
            can_answer=True,
        )
        assert a.can_answer is True
        assert a.confidence == 0.92
        assert len(a.citations) == 1

    def test_can_answer_true_without_citations_raises(self):
        """The custom validator: if you claim you can answer, you must cite."""
        with pytest.raises(ValidationError, match="no citations provided"):
            CitedAnswer(
                answer="Some answer",
                citations=[],
                confidence=0.85,
                can_answer=True,
            )

    def test_can_answer_false_without_citations_is_valid(self):
        """Cite-or-refuse path: can_answer=False needs no citations."""
        a = CitedAnswer(
            answer="I don't have enough information to answer this.",
            citations=[],
            confidence=0.3,
            can_answer=False,
        )
        assert a.can_answer is False
        assert len(a.citations) == 0

    def test_confidence_below_zero_raises(self):
        with pytest.raises(ValidationError):
            CitedAnswer(
                answer="test", citations=[], confidence=-0.1, can_answer=False
            )

    def test_confidence_above_one_raises(self):
        with pytest.raises(ValidationError):
            CitedAnswer(
                answer="test", citations=[], confidence=1.5, can_answer=False
            )

    def test_confidence_at_boundaries(self, valid_citation):
        """0.0 and 1.0 are both valid confidence values."""
        a0 = CitedAnswer(
            answer="test", citations=[], confidence=0.0, can_answer=False
        )
        assert a0.confidence == 0.0

        a1 = CitedAnswer(
            answer="test",
            citations=[valid_citation],
            confidence=1.0,
            can_answer=True,
        )
        assert a1.confidence == 1.0

    def test_empty_answer_raises(self):
        with pytest.raises(ValidationError):
            CitedAnswer(
                answer="", citations=[], confidence=0.5, can_answer=False
            )

    def test_multiple_citations(self, valid_citation):
        c2 = Citation(
            act_name="MSME Development Act 2006",
            section="15",
            quote="The buyer shall make payment...",
        )
        a = CitedAnswer(
            answer="Multiple acts apply.",
            citations=[valid_citation, c2],
            confidence=0.88,
            can_answer=True,
        )
        assert len(a.citations) == 2
        assert a.citations[1].act_name == "MSME Development Act 2006"


# ===================================================================
# CorpusChunk tests
# ===================================================================

class TestCorpusChunk:
    """CorpusChunk model — internal ingestion model."""

    def test_valid_chunk(self):
        c = CorpusChunk(
            act_name="Indian Contract Act 1872",
            section_number="27",
            section_title="Agreements in restraint of trade void",
            chapter="II",
            text="Every agreement by which any one is restrained...",
            source="mratanusarkar/Indian-Laws",
        )
        assert c.version == "v1"
        assert c.act_name == "Indian Contract Act 1872"

    def test_minimal_chunk_no_optionals(self):
        c = CorpusChunk(
            act_name="ICA 1872",
            section_number="1",
            text="Short title and commencement.",
            source="test",
        )
        assert c.section_title is None
        assert c.chapter is None

    def test_empty_text_raises(self):
        with pytest.raises(ValidationError):
            CorpusChunk(
                act_name="ICA",
                section_number="1",
                text="",
                source="test",
            )

    def test_to_payload(self):
        c = CorpusChunk(
            act_name="Indian Contract Act 1872",
            section_number="27",
            text="Every agreement...",
            source="test",
        )
        payload = c.to_payload()
        assert isinstance(payload, dict)
        assert payload["act_name"] == "Indian Contract Act 1872"
        assert payload["section_number"] == "27"
        # None fields excluded
        assert "section_title" not in payload
        assert "chapter" not in payload

    # ---------------------------------------------------------------
    # Dedup key normalization tests
    # ---------------------------------------------------------------

    def test_dedup_key_strips_the_and_year(self):
        c = CorpusChunk(
            act_name="The Indian Contract Act 1872",
            section_number="27",
            text="text",
            source="test",
        )
        assert c.dedup_key == ("indian contract act", "27")

    def test_dedup_key_lowercases(self):
        c = CorpusChunk(
            act_name="MSME DEVELOPMENT ACT 2006",
            section_number="15",
            text="text",
            source="test",
        )
        assert c.dedup_key == ("msme development act", "15")

    def test_dedup_key_handles_no_year(self):
        c = CorpusChunk(
            act_name="Constitution of India",
            section_number="19",
            text="text",
            source="test",
        )
        # "of india" is not a year, so it stays
        assert c.dedup_key == ("constitution of india", "19")

    def test_dedup_key_collapses_whitespace(self):
        c = CorpusChunk(
            act_name="The  Indian   Contract   Act  1872",
            section_number=" 27 ",
            text="text",
            source="test",
        )
        assert c.dedup_key == ("indian contract act", "27")

    def test_dedup_key_matching_across_datasets(self):
        """Two chunks from different datasets with the same Act + section
        should produce the same dedup key."""
        c1 = CorpusChunk(
            act_name="The Indian Contract Act 1872",
            section_number="27",
            text="Version from dataset A",
            source="dataset_a",
        )
        c2 = CorpusChunk(
            act_name="Indian Contract Act",
            section_number="27",
            text="Version from dataset B",
            source="dataset_b",
        )
        assert c1.dedup_key == c2.dedup_key
