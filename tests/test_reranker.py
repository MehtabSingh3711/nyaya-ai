"""Tests for nyaya_ai.retrieval.reranker — Cross-encoder reranking (ONNX FastEmbed).

All tests mock the TextCrossEncoder model — no real model download or ONNX execution required.
"""

import pytest
from unittest.mock import MagicMock, patch

from nyaya_ai.config import RERANKER_MODEL


@pytest.fixture
def mock_reranker():
    """Create a Reranker with a mocked TextCrossEncoder model."""
    with patch("fastembed.rerank.cross_encoder.TextCrossEncoder") as MockTCE:
        mock_model = MagicMock()
        MockTCE.return_value = mock_model

        from nyaya_ai.retrieval.reranker import Reranker

        reranker = Reranker.__new__(Reranker)
        reranker._model = mock_model
        yield reranker, mock_model


class TestReranker:

    def test_rerank_returns_top_k(self, mock_reranker):
        """Reranker should return exactly top_k results."""
        reranker, mock_model = mock_reranker

        candidates = [
            {"text": f"Section {i} text", "act_name": f"Act {i}", "score": 0.5}
            for i in range(10)
        ]

        # FastEmbed's rerank returns float scores in the original order
        mock_model.rerank.return_value = [0.9 - (i * 0.1) for i in range(10)]

        results = reranker.rerank(
            query="test query",
            candidates=candidates,
            top_k=5,
        )

        assert len(results) == 5
        mock_model.rerank.assert_called_once()

    def test_rerank_sorts_by_score(self, mock_reranker):
        """Results should be sorted by rerank_score descending."""
        reranker, mock_model = mock_reranker

        candidates = [
            {"text": "low relevance", "act_name": "Act A", "score": 0.9},
            {"text": "high relevance", "act_name": "Act B", "score": 0.5},
            {"text": "medium relevance", "act_name": "Act C", "score": 0.7},
        ]

        # Mock returns scores in the original candidate order: Act A (0.10), Act B (0.95), Act C (0.50)
        mock_model.rerank.return_value = [0.10, 0.95, 0.50]

        results = reranker.rerank(
            query="test query",
            candidates=candidates,
            top_k=3,
        )

        # Expected sort order: Act B (0.95), Act C (0.50), Act A (0.10)
        assert results[0]["act_name"] == "Act B"
        assert results[1]["act_name"] == "Act C"
        assert results[2]["act_name"] == "Act A"

    def test_rerank_adds_rerank_score(self, mock_reranker):
        """Each result should have a rerank_score field."""
        reranker, mock_model = mock_reranker

        candidates = [
            {"text": "some text", "act_name": "ICA", "score": 0.8},
        ]
        mock_model.rerank.return_value = [0.92]

        results = reranker.rerank(query="test", candidates=candidates, top_k=1)

        assert "rerank_score" in results[0]
        assert results[0]["rerank_score"] == pytest.approx(0.92)

    def test_rerank_preserves_original_score(self, mock_reranker):
        """Original retrieval score should be preserved."""
        reranker, mock_model = mock_reranker

        candidates = [
            {"text": "some text", "act_name": "ICA", "score": 0.85},
        ]
        mock_model.rerank.return_value = [0.92]

        results = reranker.rerank(query="test", candidates=candidates, top_k=1)

        assert results[0]["score"] == 0.85
        assert results[0]["rerank_score"] == pytest.approx(0.92)

    def test_rerank_empty_candidates(self, mock_reranker):
        """Should return empty list for empty candidates."""
        reranker, mock_model = mock_reranker

        results = reranker.rerank(query="test", candidates=[], top_k=5)

        assert results == []
        mock_model.rerank.assert_not_called()

    def test_rerank_preserves_payload_fields(self, mock_reranker):
        """All original payload fields should be preserved."""
        reranker, mock_model = mock_reranker

        candidates = [
            {
                "text": "Agreement in restraint of trade",
                "act_name": "ICA 1872",
                "section_number": "27",
                "section_title": "Restraint of trade",
                "score": 0.8,
                "source": "mratanusarkar",
            },
        ]
        mock_model.rerank.return_value = [0.95]

        results = reranker.rerank(query="non-compete", candidates=candidates, top_k=1)

        assert results[0]["act_name"] == "ICA 1872"
        assert results[0]["section_number"] == "27"
        assert results[0]["section_title"] == "Restraint of trade"
        assert results[0]["source"] == "mratanusarkar"

    def test_rerank_top_k_larger_than_candidates(self, mock_reranker):
        """When top_k > len(candidates), return all candidates."""
        reranker, mock_model = mock_reranker

        candidates = [
            {"text": "text 1", "score": 0.8},
            {"text": "text 2", "score": 0.7},
        ]
        mock_model.rerank.return_value = [0.9, 0.8]

        results = reranker.rerank(query="test", candidates=candidates, top_k=10)

        assert len(results) == 2

    def test_rerank_builds_pairs_with_context(self, mock_reranker):
        """Cross-encoder pairs should include act_name + section prefix."""
        reranker, mock_model = mock_reranker

        candidates = [
            {"text": "some clause text", "act_name": "ICA 1872", "section_number": "27", "score": 0.8},
        ]
        mock_model.rerank.return_value = [0.9]

        reranker.rerank(query="non-compete", candidates=candidates, top_k=1)

        # Verify the args passed to fastembed rerank
        call_kwargs = mock_model.rerank.call_args.kwargs
        assert call_kwargs["query"] == "non-compete"
        
        prefixed_docs = call_kwargs["documents"]
        assert len(prefixed_docs) == 1
        assert "ICA 1872" in prefixed_docs[0]
        assert "Section 27" in prefixed_docs[0]
        assert "some clause text" in prefixed_docs[0]
