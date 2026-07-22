"""Tests for nyaya_ai.retrieval.embedder — BGE-M3 hybrid wrapper.

All tests mock the BGEM3FlagModel — no actual model download.
Tests cover dense-only, sparse-only, and hybrid (dense + sparse) methods.
"""

import numpy as np
import pytest
from unittest.mock import MagicMock, patch

from nyaya_ai.retrieval.embedder import Embedder, HybridVectors, HybridQueryVectors


@pytest.fixture
def mock_embedder():
    """Create an Embedder with a mocked BGEM3FlagModel."""
    with patch("FlagEmbedding.BGEM3FlagModel") as MockBGE:
        mock_model = MagicMock()
        mock_tokenizer = MagicMock()

        # Mock tokenizer for sparse token conversion
        mock_tokenizer.convert_tokens_to_ids.side_effect = lambda tokens: [
            hash(t) % 30000 for t in tokens
        ]
        mock_model.tokenizer = mock_tokenizer

        def mock_encode(
            texts,
            batch_size=32,
            return_dense=True,
            return_sparse=False,
            return_colbert_vecs=False,
            verbose=True,
            **kwargs,
        ):
            n = len(texts) if isinstance(texts, list) else 1
            result = {}

            if return_dense:
                vecs = np.random.randn(n, 1024).astype(np.float32)
                norms = np.linalg.norm(vecs, axis=1, keepdims=True)
                vecs = vecs / norms
                result["dense_vecs"] = vecs

            if return_sparse:
                # Simulate lexical weights as {token_string: weight}
                result["lexical_weights"] = [
                    {"agreement": 0.8, "restraint": 0.6, "void": 0.4}
                    for _ in range(n)
                ]

            return result

        mock_model.encode = mock_encode
        MockBGE.return_value = mock_model

        embedder = Embedder.__new__(Embedder)
        embedder._model = mock_model

        yield embedder


class TestEmbedderDense:
    """Dense-only embedding tests (backward compatible)."""

    def test_embed_documents_returns_correct_count(self, mock_embedder):
        texts = ["text one", "text two", "text three"]
        vectors = mock_embedder.embed_documents(texts)
        assert len(vectors) == 3

    def test_embed_documents_returns_1024_dims(self, mock_embedder):
        vectors = mock_embedder.embed_documents(["some legal text"])
        assert len(vectors[0]) == 1024

    def test_embed_documents_returns_lists(self, mock_embedder):
        vectors = mock_embedder.embed_documents(["text"])
        assert isinstance(vectors, list)
        assert isinstance(vectors[0], list)
        assert isinstance(vectors[0][0], float)

    def test_embed_documents_normalized(self, mock_embedder):
        """Embedding vectors should be L2-normalized (unit length)."""
        vectors = mock_embedder.embed_documents(["test text"])
        vec = np.array(vectors[0])
        norm = np.linalg.norm(vec)
        assert abs(norm - 1.0) < 0.01

    def test_embed_query_returns_1024_dims(self, mock_embedder):
        vector = mock_embedder.embed_query("what is section 27?")
        assert len(vector) == 1024

    def test_embed_query_returns_list(self, mock_embedder):
        vector = mock_embedder.embed_query("test")
        assert isinstance(vector, list)
        assert isinstance(vector[0], float)

    def test_embed_query_normalized(self, mock_embedder):
        vector = mock_embedder.embed_query("test query")
        norm = np.linalg.norm(np.array(vector))
        assert abs(norm - 1.0) < 0.01

    def test_embed_empty_batch(self, mock_embedder):
        vectors = mock_embedder.embed_documents([])
        assert len(vectors) == 0


class TestEmbedderHybrid:
    """Hybrid (dense + sparse) embedding tests."""

    def test_hybrid_documents_returns_named_tuple(self, mock_embedder):
        result = mock_embedder.embed_documents_hybrid(["text"])
        assert isinstance(result, HybridVectors)
        assert hasattr(result, "dense")
        assert hasattr(result, "sparse")

    def test_hybrid_documents_dense_shape(self, mock_embedder):
        result = mock_embedder.embed_documents_hybrid(["text 1", "text 2"])
        assert len(result.dense) == 2
        assert len(result.dense[0]) == 1024

    def test_hybrid_documents_sparse_shape(self, mock_embedder):
        result = mock_embedder.embed_documents_hybrid(["text 1", "text 2"])
        assert len(result.sparse) == 2
        # Each sparse dict should have int keys and float values
        for sparse_dict in result.sparse:
            assert isinstance(sparse_dict, dict)
            for key, value in sparse_dict.items():
                assert isinstance(key, int)
                assert isinstance(value, float)

    def test_hybrid_query_returns_named_tuple(self, mock_embedder):
        result = mock_embedder.embed_query_hybrid("test query")
        assert isinstance(result, HybridQueryVectors)
        assert hasattr(result, "dense")
        assert hasattr(result, "sparse")

    def test_hybrid_query_dense_is_single_vector(self, mock_embedder):
        result = mock_embedder.embed_query_hybrid("test query")
        assert len(result.dense) == 1024
        assert isinstance(result.dense, list)

    def test_hybrid_query_sparse_is_dict(self, mock_embedder):
        result = mock_embedder.embed_query_hybrid("test query")
        assert isinstance(result.sparse, dict)
        for key, value in result.sparse.items():
            assert isinstance(key, int)
            assert isinstance(value, float)

    def test_hybrid_query_sparse_has_entries(self, mock_embedder):
        """Sparse vector should have at least some non-zero entries."""
        result = mock_embedder.embed_query_hybrid("test query")
        assert len(result.sparse) > 0

    @patch("requests.post")
    def test_remote_embedding_service(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "dense": [0.1] * 1024,
            "sparse": {"101": 0.5, "202": 0.8}
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        embedder = Embedder.__new__(Embedder)
        embedder._remote_url = "https://test-kaggle.trycloudflare.com"
        embedder._model = None

        res = embedder.embed_query_hybrid("sample query")
        assert len(res.dense) == 1024
        assert res.sparse == {101: 0.5, 202: 0.8}
        mock_post.assert_called_once()
