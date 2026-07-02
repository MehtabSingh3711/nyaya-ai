"""Tests for nyaya_ai.llm.cascade — confidence-threshold LLM cascade.

All tests mock the Ollama HTTP call — no real LLM inference.
"""

import json

import pytest
from unittest.mock import patch, MagicMock

from nyaya_ai.llm.cascade import cascade_query, _format_context, _parse_response
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


# ===================================================================
# cascade_query tests
# ===================================================================

class TestCascadeQuery:

    @patch("nyaya_ai.llm.cascade._call_ollama")
    def test_valid_response_parses_correctly(self, mock_ollama):
        mock_ollama.return_value = VALID_RESPONSE_JSON
        result = cascade_query("Is non-compete enforceable?", SAMPLE_CHUNKS)

        assert isinstance(result, CitedAnswer)
        assert result.can_answer is True
        assert result.confidence == 0.92
        assert result.citations[0].section == "27"
        assert "restrained" in result.citations[0].quote

    @patch("nyaya_ai.llm.cascade._call_ollama")
    def test_low_confidence_sets_cant_answer(self, mock_ollama):
        """Confidence below CONFIDENCE_THRESHOLD → can_answer forced to False."""
        mock_ollama.return_value = LOW_CONFIDENCE_RESPONSE_JSON
        result = cascade_query("Some vague question", SAMPLE_CHUNKS)

        assert result.can_answer is False
        assert result.confidence == 0.4

    @patch("nyaya_ai.llm.cascade._call_ollama")
    def test_cite_or_refuse_response(self, mock_ollama):
        mock_ollama.return_value = CANT_ANSWER_RESPONSE_JSON
        result = cascade_query("What is criminal law?", SAMPLE_CHUNKS)

        assert result.can_answer is False
        assert len(result.citations) == 0

    @patch("nyaya_ai.llm.cascade._call_ollama")
    def test_retry_on_validation_failure(self, mock_ollama):
        """First call returns garbage, second returns valid JSON."""
        mock_ollama.side_effect = [
            "not valid json",
            VALID_RESPONSE_JSON,
        ]
        result = cascade_query("Test question", SAMPLE_CHUNKS)

        assert isinstance(result, CitedAnswer)
        assert result.can_answer is True
        assert mock_ollama.call_count == 2

    @patch("nyaya_ai.llm.cascade._call_ollama")
    def test_fallback_after_all_retries_exhausted(self, mock_ollama):
        """All retry attempts return garbage → fallback response."""
        mock_ollama.return_value = "still not valid json"
        result = cascade_query("Test question", SAMPLE_CHUNKS)

        assert isinstance(result, CitedAnswer)
        assert result.can_answer is False
        assert result.confidence == 0.0
        assert "Unable to parse" in result.answer

    @patch("nyaya_ai.llm.cascade._call_ollama")
    def test_connection_error_returns_fallback(self, mock_ollama):
        """Ollama not running → graceful fallback, not a crash."""
        mock_ollama.side_effect = ConnectionError("Cannot connect to Ollama")
        result = cascade_query("Test question", SAMPLE_CHUNKS)

        assert isinstance(result, CitedAnswer)
        assert result.can_answer is False
        assert "language model" in result.answer.lower()

    @patch("nyaya_ai.llm.cascade._call_ollama")
    def test_never_raises(self, mock_ollama):
        """cascade_query should NEVER raise — always returns a CitedAnswer."""
        mock_ollama.side_effect = RuntimeError("Unexpected error")

        # This should not raise — the function catches all exceptions
        # If it does raise, the test fails
        try:
            result = cascade_query("Test", SAMPLE_CHUNKS)
            # If we get here, it returned a fallback
            assert isinstance(result, CitedAnswer)
        except RuntimeError:
            # The cascade let an exception escape — this is a bug
            pytest.fail("cascade_query raised an exception instead of returning a fallback")
