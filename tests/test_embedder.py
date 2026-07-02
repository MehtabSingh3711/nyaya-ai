"""Tests for nyaya_ai.retrieval.embedder — BGE-M3 wrapper.

All tests mock the SentenceTransformer model — no actual model download.
"""

import numpy as np
import pytest
from unittest.mock import MagicMock, patch

from nyaya_ai.retrieval.embedder import Embedder


@pytest.fixture
def mock_embedder():
    """Create an Embedder with a mocked SentenceTransformer."""
    with patch("sentence_transformers.SentenceTransformer") as MockST:
        mock_model = MagicMock()

        # embed_documents: batch of 2 texts → 2 vectors of dim 1024, normalized
        def mock_encode(texts, normalize_embeddings=True, show_progress_bar=False, batch_size=32):
            if isinstance(texts, str):
                # Single text (embed_query path)
                vec = np.random.randn(1024).astype(np.float32)
                if normalize_embeddings:
                    vec = vec / np.linalg.norm(vec)
                return vec
            else:
                # Batch (embed_documents path)
                vecs = np.random.randn(len(texts), 1024).astype(np.float32)
                if normalize_embeddings:
                    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
                    vecs = vecs / norms
                return vecs

        mock_model.encode = mock_encode
        MockST.return_value = mock_model

        embedder = Embedder()
        yield embedder


class TestEmbedder:
    """Embedder — BGE-M3 wrapper tests."""

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
        assert abs(norm - 1.0) < 0.01  # approximately unit length

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
