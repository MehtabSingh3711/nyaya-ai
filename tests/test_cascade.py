"""Tests for nyaya_ai.llm.cascade — 3-tier cloud LLM cascade.

All tests mock the LLM HTTP calls — no real API calls.
"""

import json

import pytest
from unittest.mock import patch, MagicMock

from nyaya_ai.llm.cascade import (
    cascade_query,
    _format_context,
    _extract_json,
    _parse_response,
    _try_tier,
)
from nyaya_ai.schemas import CitedAnswer


# ===================================================================
# Fixtures
# ===================================================================

VALID_RESPONSE_JSON = json.dumps({
    "answer": "Non-compete clauses are void under Section 27 of the Indian Contract Act 1872.",
    "citations": [
        {
            "source_type": "statute",
            "act_name": "Indian Contract Act 1872",
            "section": "27",
            "quote": "Every agreement by which any one is restrained from exercising a lawful profession, trade or business of any kind, is to that extent void.",
        }
    ],
    "confidence": 0.92,
    "can_answer": True,
})

LOW_CONFIDENCE_RESPONSE_JSON = json.dumps({
    "answer": "There may be some provisions but I am not certain.",
    "citations": [
        {
            "source_type": "statute",
            "act_name": "Indian Contract Act 1872",
            "section": "27",
            "quote": "Every agreement...",
        }
    ],
    "confidence": 0.4,
    "can_answer": True,
})

CANT_ANSWER_RESPONSE_JSON = json.dumps({
    "answer": "The provided context does not contain information about criminal law.",
    "citations": [],
    "confidence": 0.1,
    "can_answer": False,
})

SAMPLE_CHUNKS = [
    {
        "act_name": "Indian Contract Act 1872",
        "section_number": "27",
        "text": "Every agreement by which any one is restrained...",
        "score": 0.92,
    },
    {
        "act_name": "Indian Contract Act 1872",
        "section_number": "28",
        "text": "Agreements in restraint of legal proceedings...",
        "score": 0.85,
    },
]


# ===================================================================
# _format_context tests
# ===================================================================

class TestFormatContext:

    def test_formats_numbered_sections(self):
        result = _format_context(SAMPLE_CHUNKS)
        assert "[Section 1]" in result
        assert "[Section 2]" in result
        assert "Indian Contract Act 1872" in result
        assert "Section 27" in result

    def test_empty_chunks(self):
        result = _format_context([])
        assert "No context" in result


# ===================================================================
# _extract_json tests
# ===================================================================

class TestExtractJson:

    def test_clean_json(self):
        raw = '{"answer": "test", "confidence": 0.9}'
        assert _extract_json(raw) == raw

    def test_strips_markdown_fences(self):
        raw = '```json\n{"answer": "test"}\n```'
        assert _extract_json(raw) == '{"answer": "test"}'

    def test_strips_text_before_json(self):
        raw = 'Here is the answer:\n{"answer": "test"}'
        assert _extract_json(raw) == '{"answer": "test"}'

    def test_no_json_raises(self):
        with pytest.raises(ValueError, match="No JSON"):
            _extract_json("just plain text")

    def test_nested_braces(self):
        raw = '{"a": {"b": "c"}, "d": "e"}'
        assert _extract_json(raw) == raw


# ===================================================================
# _parse_response tests
# ===================================================================

class TestParseResponse:

    def test_valid_json_parses(self):
        answer = _parse_response(VALID_RESPONSE_JSON)
        assert isinstance(answer, CitedAnswer)
        assert answer.can_answer is True
        assert answer.confidence == 0.92
        assert len(answer.citations) == 1

    def test_invalid_json_raises(self):
        with pytest.raises((ValueError, Exception)):
            _parse_response("not valid json at all")

    def test_missing_fields_raises(self):
        with pytest.raises((ValueError, Exception)):
            _parse_response(json.dumps({"answer": "test"}))

    def test_fenced_json_parses(self):
        """JSON wrapped in markdown fences should still parse."""
        fenced = f"```json\n{VALID_RESPONSE_JSON}\n```"
        answer = _parse_response(fenced)
        assert answer.can_answer is True


# ===================================================================
# cascade_query — full cascade tests
# ===================================================================

class TestCascadeQuery:

    @patch("nyaya_ai.llm.cascade._call_groq")
    def test_tier1_valid_response(self, mock_groq):
        """Tier 1 returns valid JSON → answer returned, no escalation."""
        mock_groq.return_value = VALID_RESPONSE_JSON
        result = cascade_query("Is non-compete enforceable?", SAMPLE_CHUNKS)

        assert isinstance(result, CitedAnswer)
        assert result.can_answer is True
        assert result.confidence == 0.92
        assert result.citations[0].section == "27"
        mock_groq.assert_called_once()

    @patch("nyaya_ai.llm.cascade._call_groq")
    def test_low_confidence_sets_cant_answer(self, mock_groq):
        """Confidence below threshold → can_answer forced to False."""
        mock_groq.return_value = LOW_CONFIDENCE_RESPONSE_JSON
        result = cascade_query("Some vague question", SAMPLE_CHUNKS)

        assert result.can_answer is False
        assert result.confidence == 0.4

    @patch("nyaya_ai.llm.cascade._call_groq")
    def test_cite_or_refuse_response(self, mock_groq):
        mock_groq.return_value = CANT_ANSWER_RESPONSE_JSON
        result = cascade_query("What is criminal law?", SAMPLE_CHUNKS)

        assert result.can_answer is False
        assert len(result.citations) == 0

    @patch("nyaya_ai.llm.cascade._call_groq")
    def test_retry_on_validation_failure(self, mock_groq):
        """First call garbage, second call valid → answer returned."""
        mock_groq.side_effect = [
            "not valid json",
            VALID_RESPONSE_JSON,
        ]
        result = cascade_query("Test question", SAMPLE_CHUNKS)

        assert isinstance(result, CitedAnswer)
        assert result.can_answer is True
        assert mock_groq.call_count == 2

    @patch("nyaya_ai.llm.cascade._call_openrouter")
    @patch("nyaya_ai.llm.cascade._call_gemini")
    @patch("nyaya_ai.llm.cascade._call_groq")
    def test_escalation_tier1_to_tier2(self, mock_groq, mock_gemini, mock_openrouter):
        """Tier 1 fails → escalates to Tier 2 which succeeds."""
        mock_groq.side_effect = ConnectionError("Groq down")
        mock_gemini.return_value = VALID_RESPONSE_JSON

        result = cascade_query("Test question", SAMPLE_CHUNKS)

        assert isinstance(result, CitedAnswer)
        assert result.can_answer is True
        mock_groq.assert_called_once()
        mock_gemini.assert_called_once()
        mock_openrouter.assert_not_called()

    @patch("nyaya_ai.llm.cascade._call_openrouter")
    @patch("nyaya_ai.llm.cascade._call_gemini")
    @patch("nyaya_ai.llm.cascade._call_groq")
    def test_escalation_all_tiers_to_tier3(self, mock_groq, mock_gemini, mock_openrouter):
        """Tier 1 and 2 fail → Tier 3 succeeds."""
        mock_groq.side_effect = ConnectionError("Groq down")
        mock_gemini.side_effect = ConnectionError("Gemini down")
        mock_openrouter.return_value = VALID_RESPONSE_JSON

        result = cascade_query("Test question", SAMPLE_CHUNKS)

        assert isinstance(result, CitedAnswer)
        assert result.can_answer is True
        mock_openrouter.assert_called_once()

    @patch("nyaya_ai.llm.cascade._call_openrouter")
    @patch("nyaya_ai.llm.cascade._call_gemini")
    @patch("nyaya_ai.llm.cascade._call_groq")
    def test_all_tiers_fail_returns_fallback(self, mock_groq, mock_gemini, mock_openrouter):
        """All 3 tiers fail → cite-or-refuse fallback."""
        mock_groq.side_effect = ConnectionError("Groq down")
        mock_gemini.side_effect = ConnectionError("Gemini down")
        mock_openrouter.side_effect = ConnectionError("OpenRouter down")

        result = cascade_query("Test question", SAMPLE_CHUNKS)

        assert isinstance(result, CitedAnswer)
        assert result.can_answer is False
        assert result.confidence == 0.0
        assert "Unable to get" in result.answer

    @patch("nyaya_ai.llm.cascade._call_openrouter")
    @patch("nyaya_ai.llm.cascade._call_gemini")
    @patch("nyaya_ai.llm.cascade._call_groq")
    def test_parse_failure_escalates(self, mock_groq, mock_gemini, mock_openrouter):
        """Tier 1 returns garbage on all retries → escalates to Tier 2."""
        mock_groq.return_value = "still not valid json"
        mock_gemini.return_value = VALID_RESPONSE_JSON

        result = cascade_query("Test question", SAMPLE_CHUNKS)

        assert isinstance(result, CitedAnswer)
        assert result.can_answer is True
        # Groq called 1 + MAX_RETRIES times, Gemini called once
        assert mock_groq.call_count >= 2
        mock_gemini.assert_called_once()

    @patch("nyaya_ai.llm.cascade._call_openrouter")
    @patch("nyaya_ai.llm.cascade._call_gemini")
    @patch("nyaya_ai.llm.cascade._call_groq")
    def test_never_raises(self, mock_groq, mock_gemini, mock_openrouter):
        """cascade_query should NEVER raise — always returns a CitedAnswer."""
        mock_groq.side_effect = RuntimeError("Unexpected")
        mock_gemini.side_effect = RuntimeError("Unexpected")
        mock_openrouter.side_effect = RuntimeError("Unexpected")

        result = cascade_query("Test", SAMPLE_CHUNKS)

        assert isinstance(result, CitedAnswer)
        assert result.can_answer is False
