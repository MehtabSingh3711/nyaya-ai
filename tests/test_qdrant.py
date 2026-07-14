"""Tests for nyaya_ai.store.qdrant — Qdrant collection management (hybrid).

All tests mock the QdrantClient — no real Qdrant instance required.
Tests cover both hybrid (dense + sparse) and dense-only fallback paths.
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from types import SimpleNamespace

from nyaya_ai.store.qdrant import (
    create_collection,
    upsert_chunks,
    search,
    get_point_count,
)
from nyaya_ai.schemas import CorpusChunk


def _make_chunk(act_name: str = "ICA 1872", section: str = "27") -> CorpusChunk:
    return CorpusChunk(
        act_name=act_name,
        section_number=section,
        text="Every agreement by which any one is restrained...",
        source="test",
    )


@pytest.fixture
def mock_client():
    """Patch _get_client to return a mock QdrantClient."""
    with patch("nyaya_ai.store.qdrant._get_client") as mock_get:
        client = MagicMock()
        mock_get.return_value = client
        yield client


# ===================================================================
# create_collection tests
# ===================================================================

class TestCreateCollection:

    def test_creates_new_collection(self, mock_client):
        """When collection doesn't exist, create_collection() calls create_collection on client."""
        # No existing collections
        mock_client.get_collections.return_value = SimpleNamespace(collections=[])
        create_collection()
        mock_client.create_collection.assert_called_once()

    def test_idempotent_when_exists(self, mock_client):
        """When collection already exists, create_collection() does NOT call create_collection."""
        existing = SimpleNamespace(name="nyaya_corpus")
        mock_client.get_collections.return_value = SimpleNamespace(collections=[existing])
        create_collection()
        mock_client.create_collection.assert_not_called()

    def test_vector_config_has_dense(self, mock_client):
        """Verify the vector config includes dense named vector."""
        mock_client.get_collections.return_value = SimpleNamespace(collections=[])
        create_collection()

        call_kwargs = mock_client.create_collection.call_args
        assert call_kwargs.kwargs["collection_name"] == "nyaya_corpus"
        vectors_config = call_kwargs.kwargs["vectors_config"]
        assert "dense" in vectors_config

    def test_sparse_vector_config_present(self, mock_client):
        """Verify the collection is created with sparse vector config."""
        mock_client.get_collections.return_value = SimpleNamespace(collections=[])
        create_collection()

        call_kwargs = mock_client.create_collection.call_args
        sparse_config = call_kwargs.kwargs.get("sparse_vectors_config", {})
        assert "sparse" in sparse_config


# ===================================================================
# upsert_chunks tests
# ===================================================================

class TestUpsertChunks:

    def test_upserts_correct_count(self, mock_client):
        chunks = [_make_chunk(section=str(i)) for i in range(5)]
        vectors = [[0.1] * 1024 for _ in range(5)]
        upsert_chunks(chunks, vectors)
        # Should call upsert once (5 < batch_size of 100)
        mock_client.upsert.assert_called_once()

    def test_payload_structure_dense_only(self, mock_client):
        """When no sparse vectors provided, only dense vector is stored."""
        chunk = _make_chunk()
        vector = [[0.1] * 1024]
        upsert_chunks([chunk], vector)

        call_args = mock_client.upsert.call_args
        points = call_args.kwargs["points"]
        assert len(points) == 1

        point = points[0]
        assert "dense" in point.vector
        assert "sparse" not in point.vector
        assert point.payload["act_name"] == "ICA 1872"
        assert point.payload["section_number"] == "27"
        assert point.payload["source"] == "test"

    def test_payload_structure_with_sparse(self, mock_client):
        """When sparse vectors provided, both dense and sparse are stored."""
        chunk = _make_chunk()
        dense = [[0.1] * 1024]
        sparse = [{1: 0.5, 5: 0.3, 100: 0.1}]
        upsert_chunks([chunk], dense, sparse_vectors=sparse)

        call_args = mock_client.upsert.call_args
        points = call_args.kwargs["points"]
        point = points[0]

        assert "dense" in point.vector
        assert "sparse" in point.vector
        # Verify sparse vector structure
        sv = point.vector["sparse"]
        assert hasattr(sv, "indices")
        assert hasattr(sv, "values")

    def test_mismatched_lengths_raises(self, mock_client):
        chunks = [_make_chunk()]
        vectors = [[0.1] * 1024, [0.2] * 1024]  # 2 vectors but 1 chunk
        with pytest.raises(ValueError, match="same length"):
            upsert_chunks(chunks, vectors)

    def test_mismatched_sparse_lengths_raises(self, mock_client):
        """Sparse vectors must match chunks length."""
        chunks = [_make_chunk(), _make_chunk(section="28")]
        vectors = [[0.1] * 1024, [0.2] * 1024]
        sparse = [{1: 0.5}]  # Only 1 sparse but 2 chunks
        with pytest.raises(ValueError, match="same length"):
            upsert_chunks(chunks, vectors, sparse_vectors=sparse)

    def test_empty_chunks_skips(self, mock_client):
        upsert_chunks([], [])
        mock_client.upsert.assert_not_called()

    def test_batches_large_upserts(self, mock_client):
        """More than 100 chunks should be upserted in multiple batches."""
        chunks = [_make_chunk(section=str(i)) for i in range(250)]
        vectors = [[0.1] * 1024 for _ in range(250)]
        upsert_chunks(chunks, vectors)
        # 250 / 100 = 3 batches
        assert mock_client.upsert.call_count == 3


# ===================================================================
# search tests
# ===================================================================

class TestSearch:

    def test_dense_only_search(self, mock_client):
        """When no sparse_vector, falls back to dense-only search."""
        mock_point = SimpleNamespace(
            payload={"act_name": "ICA 1872", "section_number": "27", "text": "..."},
            score=0.92,
        )
        mock_client.query_points.return_value = SimpleNamespace(points=[mock_point])

        results = search(query_vector=[0.1] * 1024, top_k=5)
        assert len(results) == 1
        assert results[0]["act_name"] == "ICA 1872"
        assert results[0]["score"] == 0.92

        # Verify dense-only path (no prefetch)
        call_kwargs = mock_client.query_points.call_args.kwargs
        assert "prefetch" not in call_kwargs or call_kwargs.get("prefetch") is None

    def test_hybrid_search_with_sparse(self, mock_client):
        """When sparse_vector provided, uses prefetch + RRF fusion."""
        mock_point = SimpleNamespace(
            payload={"act_name": "MSME Act", "section_number": "15", "text": "..."},
            score=0.85,
        )
        mock_client.query_points.return_value = SimpleNamespace(points=[mock_point])

        sparse = {1: 0.5, 10: 0.3}
        results = search(
            query_vector=[0.1] * 1024,
            top_k=5,
            sparse_vector=sparse,
        )
        assert len(results) == 1
        assert results[0]["act_name"] == "MSME Act"

        # Verify hybrid path (prefetch present)
        call_kwargs = mock_client.query_points.call_args.kwargs
        assert call_kwargs.get("prefetch") is not None
        assert len(call_kwargs["prefetch"]) == 2  # dense + sparse prefetch

    def test_empty_results(self, mock_client):
        mock_client.query_points.return_value = SimpleNamespace(points=[])
        results = search(query_vector=[0.1] * 1024)
        assert results == []

    def test_multiple_results_preserve_order(self, mock_client):
        points = [
            SimpleNamespace(
                payload={"act_name": "ICA", "section_number": str(i)},
                score=0.9 - i * 0.1,
            )
            for i in range(3)
        ]
        mock_client.query_points.return_value = SimpleNamespace(points=points)
        results = search(query_vector=[0.1] * 1024, top_k=3)
        assert len(results) == 3
        assert results[0]["score"] > results[2]["score"]


# ===================================================================
# get_point_count tests
# ===================================================================

class TestGetPointCount:

    def test_returns_count(self, mock_client):
        mock_client.get_collection.return_value = SimpleNamespace(points_count=1500)
        assert get_point_count() == 1500

    def test_zero_count(self, mock_client):
        mock_client.get_collection.return_value = SimpleNamespace(points_count=0)
        assert get_point_count() == 0

    def test_none_count_returns_zero(self, mock_client):
        mock_client.get_collection.return_value = SimpleNamespace(points_count=None)
        assert get_point_count() == 0


# ===================================================================
# Collection parameterization tests
# ===================================================================

class TestCollectionParameterization:

    def test_custom_collection_create(self, mock_client):
        mock_client.get_collections.return_value = SimpleNamespace(collections=[])
        create_collection("custom_col")
        # Check custom collection was created
        mock_client.create_collection.assert_called_once()
        assert mock_client.create_collection.call_args[1]["collection_name"] == "custom_col"

    def test_custom_collection_upsert(self, mock_client):
        chunk = _make_chunk()
        upsert_chunks([chunk], [[0.1] * 1024], collection_name="custom_col")
        mock_client.upsert.assert_called_once()
        assert mock_client.upsert.call_args[1]["collection_name"] == "custom_col"

    def test_custom_collection_search(self, mock_client):
        mock_client.query_points.return_value = SimpleNamespace(points=[])
        search(query_vector=[0.1] * 1024, collection_name="custom_col")
        mock_client.query_points.assert_called_once()
        assert mock_client.query_points.call_args[1]["collection_name"] == "custom_col"

    def test_custom_collection_point_count(self, mock_client):
        mock_client.get_collection.return_value = SimpleNamespace(points_count=10)
        assert get_point_count("custom_col") == 10
        mock_client.get_collection.assert_called_once_with(collection_name="custom_col")
