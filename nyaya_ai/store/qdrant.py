"""Qdrant vector store management for Nyaya AI (ADR-003, ADR-011).

Manages the nyaya_corpus collection: creation with hybrid named vectors
(dense + sparse), upsert, hybrid search with RRF fusion, and point count.

Hybrid search pipeline:
    1. Dense prefetch (BGE-M3 cosine, top-20)
    2. Sparse prefetch (lexical weights, top-20)
    3. RRF fusion → combined ranked list
    4. (Reranking happens at the caller level, not here)

Connection errors are caught and surfaced as clear messages — no silent failures.
"""

from __future__ import annotations

import uuid

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from qdrant_client.http.exceptions import (
    ResponseHandlingException,
    UnexpectedResponse,
)
from rich.console import Console

from nyaya_ai.config import COLLECTION_NAME, EMBEDDING_DIM, QDRANT_PATH, QDRANT_URL, QDRANT_API_KEY

console = Console()

# Singleton client — file-based Qdrant must reuse the same client instance
_client: QdrantClient | None = None


def _get_client() -> QdrantClient:
    """Get or create a Qdrant client.

    Uses local file storage (QDRANT_PATH) when QDRANT_URL is None.
    Uses server mode (QDRANT_URL) when set, passing QDRANT_API_KEY if present.
    Raises ConnectionError if server mode and Qdrant is not reachable.
    """
    global _client
    if _client is not None:
        return _client

    try:
        if QDRANT_URL:
            # Docker / server mode (including Qdrant Cloud)
            _client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY, timeout=10)
            _client.get_collections()  # test connection
        else:
            # Local file-based mode (no Docker)
            _client = QdrantClient(path=QDRANT_PATH)
        return _client
    except Exception as e:
        msg = (
            f"Cannot connect to Qdrant at {QDRANT_URL}. "
            f"Is it running? Start with: docker compose up -d"
            if QDRANT_URL
            else f"Cannot open Qdrant storage at {QDRANT_PATH}: {e}"
        )
        raise ConnectionError(f"{msg}\nError: {e}") from e


def create_collection(collection_name: str = COLLECTION_NAME) -> None:
    """Create a collection with hybrid vector config (dense + sparse).

    Idempotent — does nothing if the collection already exists.
    """
    client = _get_client()

    existing = [c.name for c in client.get_collections().collections]
    if collection_name in existing:
        console.print(
            f"[yellow]Collection '{collection_name}' already exists — skipping creation.[/]"
        )
        return

    client.create_collection(
        collection_name=collection_name,
        vectors_config={
            "dense": qmodels.VectorParams(
                size=EMBEDDING_DIM,
                distance=qmodels.Distance.COSINE,
            ),
        },
        sparse_vectors_config={
            "sparse": qmodels.SparseVectorParams(),
        },
    )
    console.print(
        f"[green]Created collection '{collection_name}' "
        f"(dense={EMBEDDING_DIM}d cosine + sparse lexical).[/]"
    )


def upsert_chunks(
    chunks: list,
    vectors: list[list[float]],
    collection_name: str = COLLECTION_NAME,
    sparse_vectors: list[dict[int, float]] | None = None,
) -> None:
    """Batch upsert chunks with their embedding vectors.

    Args:
        chunks: List of CorpusChunk or ClauseExtraction objects (uses to_payload() for payload).
        vectors: Corresponding list of dense embedding vectors.
        collection_name: Target collection name in Qdrant.
        sparse_vectors: Optional list of sparse vector dicts ({token_id: weight}).
                        If None, points are upserted with dense vectors only.

    Raises:
        ValueError: If chunks and vectors have different lengths.
        ConnectionError: If Qdrant is not reachable.
    """
    if len(chunks) != len(vectors):
        raise ValueError(
            f"chunks ({len(chunks)}) and vectors ({len(vectors)}) must have the same length"
        )

    if sparse_vectors is not None and len(chunks) != len(sparse_vectors):
        raise ValueError(
            f"chunks ({len(chunks)}) and sparse_vectors ({len(sparse_vectors)}) "
            f"must have the same length"
        )

    if not chunks:
        console.print("[yellow]No chunks to upsert — skipping.[/]")
        return

    client = _get_client()

    points = []
    for i, (chunk, dense_vec) in enumerate(zip(chunks, vectors)):
        vector_data: dict = {"dense": dense_vec}

        if sparse_vectors is not None:
            sv = sparse_vectors[i]
            vector_data["sparse"] = qmodels.SparseVector(
                indices=list(sv.keys()),
                values=list(sv.values()),
            )

        points.append(
            qmodels.PointStruct(
                id=str(uuid.uuid4()),
                vector=vector_data,
                payload=chunk.to_payload(),
            )
        )

    # Upsert in batches of 100 to avoid large payloads
    batch_size = 100
    for i in range(0, len(points), batch_size):
        batch = points[i : i + batch_size]
        client.upsert(
            collection_name=collection_name,
            points=batch,
        )

    console.print(f"[green]Upserted {len(points)} points into '{collection_name}'.[/]")


def search(
    query_vector: list[float],
    top_k: int = 5,
    collection_name: str = COLLECTION_NAME,
    sparse_vector: dict[int, float] | None = None,
) -> list[dict]:
    """Hybrid or dense-only search.

    When sparse_vector is provided, performs hybrid search using Qdrant's
    prefetch + RRF fusion (dense + sparse). When sparse_vector is None,
    falls back to dense-only cosine search (backward compatible).

    Args:
        query_vector: The query dense embedding vector (1024-dim).
        top_k: Number of results to return.
        collection_name: Target collection name in Qdrant.
        sparse_vector: Optional sparse vector dict ({token_id: weight}).
                       If provided, enables hybrid search with RRF fusion.

    Returns:
        List of dicts, each containing the payload fields plus a 'score' field.
        Sorted by descending similarity/fusion score.

    Raises:
        ConnectionError: If Qdrant is not reachable.
    """
    client = _get_client()

    if sparse_vector is not None:
        # Hybrid search: dense + sparse with RRF fusion
        sparse_qvec = qmodels.SparseVector(
            indices=list(sparse_vector.keys()),
            values=list(sparse_vector.values()),
        )

        results = client.query_points(
            collection_name=collection_name,
            prefetch=[
                qmodels.Prefetch(
                    query=query_vector,
                    using="dense",
                    limit=top_k,
                ),
                qmodels.Prefetch(
                    query=sparse_qvec,
                    using="sparse",
                    limit=top_k,
                ),
            ],
            query=qmodels.FusionQuery(fusion=qmodels.Fusion.RRF),
            limit=top_k,
        )
    else:
        # Dense-only fallback (backward compatible)
        results = client.query_points(
            collection_name=collection_name,
            query=query_vector,
            using="dense",
            limit=top_k,
        )

    hits = []
    for point in results.points:
        hit = dict(point.payload) if point.payload else {}
        hit["score"] = point.score
        hits.append(hit)

    return hits


def get_point_count(collection_name: str = COLLECTION_NAME) -> int:
    """Return the total number of points in the specified collection.

    Raises:
        ConnectionError: If Qdrant is not reachable.
    """
    client = _get_client()

    info = client.get_collection(collection_name=collection_name)
    return info.points_count or 0


def set_payload_bulk(
    payload: dict,
    collection_name: str = COLLECTION_NAME,
    filter_condition: qmodels.Filter | None = None,
) -> None:
    """Set payload fields on all points (or filtered subset) without touching vectors.

    This is a payload-only update — no re-embedding required.
    Used for backfilling amendment_status="original" on existing points.

    Args:
        payload: Dict of payload fields to set (e.g. {"amendment_status": "original"}).
        collection_name: Target collection name.
        filter_condition: Optional Qdrant filter to restrict which points are updated.
                          If None, updates ALL points in the collection.
    """
    client = _get_client()

    client.set_payload(
        collection_name=collection_name,
        payload=payload,
        points=filter_condition if filter_condition else qmodels.FilterSelector(
            filter=qmodels.Filter(must=[])
        ),
    )
    console.print(
        f"[green]Set payload {payload} on points in '{collection_name}'.[/]"
    )


def find_points_by_section(
    act_name: str,
    section_number: str,
    collection_name: str = COLLECTION_NAME,
) -> list[dict]:
    """Find existing points by act_name and section_number.

    Uses Qdrant's scroll API with payload filters to find matching points
    without needing vectors. Returns full payload + point ID for each match.

    Args:
        act_name: The Act name to search for (case-insensitive substring match).
        section_number: The section number to match exactly.
        collection_name: Target collection name.

    Returns:
        List of dicts, each containing 'id', 'act_name', 'section_number',
        'text', and all other payload fields.
    """
    client = _get_client()

    # Use must conditions: act_name match + section_number match
    scroll_filter = qmodels.Filter(
        must=[
            qmodels.FieldCondition(
                key="act_name",
                match=qmodels.MatchText(text=act_name),
            ),
            qmodels.FieldCondition(
                key="section_number",
                match=qmodels.MatchValue(value=section_number),
            ),
        ]
    )

    results, _next_offset = client.scroll(
        collection_name=collection_name,
        scroll_filter=scroll_filter,
        limit=100,
        with_payload=True,
        with_vectors=False,
    )

    hits = []
    for point in results:
        hit = dict(point.payload) if point.payload else {}
        hit["id"] = point.id
        hits.append(hit)

    return hits


def update_point_payload(
    point_ids: list[str],
    payload: dict,
    collection_name: str = COLLECTION_NAME,
) -> None:
    """Update payload fields on specific points by ID.

    Payload-only operation — vectors are not touched.

    Args:
        point_ids: List of Qdrant point ID strings to update.
        payload: Dict of payload fields to set/overwrite.
        collection_name: Target collection name.
    """
    if not point_ids:
        return

    client = _get_client()

    client.set_payload(
        collection_name=collection_name,
        payload=payload,
        points=point_ids,
    )
    console.print(
        f"[green]Updated payload on {len(point_ids)} point(s) in '{collection_name}'.[/]"
    )
