"""Tests for nyaya_ai.retrieval.reranker — Cross-encoder reranking.

All tests mock the CrossEncoder model — no real model download required.
"""

import pytest
from unittest.mock import MagicMock, patch
import numpy as np


@pytest.fixture
def mock_reranker():
    """Create a Reranker with a mocked CrossEncoder model."""
    with patch("nyaya_ai.retrieval.reranker.CrossEncoder", create=True):
        # We need to mock the import inside __init__
        with patch("sentence_transformers.CrossEncoder") as MockCE:
            mock_model = MagicMock()
            MockCE.return_value = mock_model

            # Patch the import to prevent model download
            with patch.dict("sys.modules", {"sentence_transformers": MagicMock()}):
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

        # Mock cross-encoder scores — higher scores for lower indices
        mock_model.predict.return_value = np.array([
            0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0.05
        ])

        results = reranker.rerank(
            query="test query",
            candidates=candidates,
            top_k=5,
        )

        assert len(results) == 5

    def test_rerank_sorts_by_score(self, mock_reranker):
        """Results should be sorted by rerank_score descending."""
        reranker, mock_model = mock_reranker

        candidates = [
            {"text": "low relevance", "act_name": "Act A", "score": 0.9},
            {"text": "high relevance", "act_name": "Act B", "score": 0.5},
            {"text": "medium relevance", "act_name": "Act C", "score": 0.7},
        ]

        # Cross-encoder gives different ranking than original scores
        mock_model.predict.return_value = np.array([0.1, 0.95, 0.5])

        results = reranker.rerank(
            query="test query",
            candidates=candidates,
            top_k=3,
        )

        assert results[0]["act_name"] == "Act B"  # highest rerank_score
        assert results[1]["act_name"] == "Act C"  # medium rerank_score
        assert results[2]["act_name"] == "Act A"  # lowest rerank_score

    def test_rerank_adds_rerank_score(self, mock_reranker):
        """Each result should have a rerank_score field."""
        reranker, mock_model = mock_reranker

        candidates = [
            {"text": "some text", "act_name": "ICA", "score": 0.8},
        ]
        mock_model.predict.return_value = np.array([0.92])

        results = reranker.rerank(query="test", candidates=candidates, top_k=1)

        assert "rerank_score" in results[0]
        assert results[0]["rerank_score"] == pytest.approx(0.92)

    def test_rerank_preserves_original_score(self, mock_reranker):
        """Original retrieval score should be preserved."""
        reranker, mock_model = mock_reranker

        candidates = [
            {"text": "some text", "act_name": "ICA", "score": 0.85},
        ]
        mock_model.predict.return_value = np.array([0.92])

        results = reranker.rerank(query="test", candidates=candidates, top_k=1)

        assert results[0]["score"] == 0.85
        assert results[0]["rerank_score"] == pytest.approx(0.92)

    def test_rerank_empty_candidates(self, mock_reranker):
        """Should return empty list for empty candidates."""
        reranker, mock_model = mock_reranker

        results = reranker.rerank(query="test", candidates=[], top_k=5)

        assert results == []
        mock_model.predict.assert_not_called()

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
        mock_model.predict.return_value = np.array([0.95])

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
        mock_model.predict.return_value = np.array([0.9, 0.8])

        results = reranker.rerank(query="test", candidates=candidates, top_k=10)

        assert len(results) == 2

    def test_rerank_builds_pairs_with_context(self, mock_reranker):
        """Cross-encoder pairs should include act_name + section prefix."""
        reranker, mock_model = mock_reranker

        candidates = [
            {"text": "some clause text", "act_name": "ICA 1872", "section_number": "27", "score": 0.8},
        ]
        mock_model.predict.return_value = np.array([0.9])

        reranker.rerank(query="non-compete", candidates=candidates, top_k=1)

        # Verify the pairs passed to predict
        call_args = mock_model.predict.call_args[0][0]
        assert len(call_args) == 1
        query_text, candidate_text = call_args[0]
        assert query_text == "non-compete"
        assert "ICA 1872" in candidate_text
        assert "Section 27" in candidate_text
