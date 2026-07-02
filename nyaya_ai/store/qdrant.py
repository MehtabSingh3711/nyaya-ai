"""Qdrant vector store management for Nyaya AI (ADR-003).

Manages the nyaya_corpus collection: creation, upsert, dense search,
and point count verification. All config read from nyaya_ai.config.

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

from nyaya_ai.config import COLLECTION_NAME, EMBEDDING_DIM, QDRANT_URL
from nyaya_ai.schemas import CorpusChunk

console = Console()


def _get_client() -> QdrantClient:
    """Create a Qdrant client. Raises ConnectionError if Qdrant is not reachable."""
    try:
        client = QdrantClient(url=QDRANT_URL, timeout=10)
        # Test connection with a lightweight call
        client.get_collections()
        return client
    except Exception as e:
        raise ConnectionError(
            f"Cannot connect to Qdrant at {QDRANT_URL}. "
            f"Is it running? Start with: docker compose up -d\n"
            f"Error: {e}"
        ) from e


def create_collection() -> None:
    """Create the nyaya_corpus collection with dense vector config.

    Idempotent — does nothing if the collection already exists.
    """
    client = _get_client()

    existing = [c.name for c in client.get_collections().collections]
    if COLLECTION_NAME in existing:
        console.print(
            f"[yellow]Collection '{COLLECTION_NAME}' already exists — skipping creation.[/]"
        )
        return

    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config={
            "dense": qmodels.VectorParams(
                size=EMBEDDING_DIM,
                distance=qmodels.Distance.COSINE,
            ),
        },
    )
    console.print(f"[green]Created collection '{COLLECTION_NAME}' (dim={EMBEDDING_DIM}, cosine).[/]")


def upsert_chunks(
    chunks: list[CorpusChunk],
    vectors: list[list[float]],
) -> None:
    """Batch upsert chunks with their embedding vectors into nyaya_corpus.

    Args:
        chunks: List of CorpusChunk objects (uses to_payload() for the payload).
        vectors: Corresponding list of dense embedding vectors.

    Raises:
        ValueError: If chunks and vectors have different lengths.
        ConnectionError: If Qdrant is not reachable.
    """
    if len(chunks) != len(vectors):
        raise ValueError(
            f"chunks ({len(chunks)}) and vectors ({len(vectors)}) must have the same length"
        )

    if not chunks:
        console.print("[yellow]No chunks to upsert — skipping.[/]")
        return

    client = _get_client()

    points = [
        qmodels.PointStruct(
            id=str(uuid.uuid4()),
            vector={"dense": vector},
            payload=chunk.to_payload(),
        )
        for chunk, vector in zip(chunks, vectors)
    ]

    # Upsert in batches of 100 to avoid large payloads
    batch_size = 100
    for i in range(0, len(points), batch_size):
        batch = points[i : i + batch_size]
        client.upsert(
            collection_name=COLLECTION_NAME,
            points=batch,
        )

    console.print(f"[green]Upserted {len(points)} points into '{COLLECTION_NAME}'.[/]")


def search(
    query_vector: list[float],
    top_k: int = 5,
) -> list[dict]:
    """Dense cosine search against nyaya_corpus.

    Args:
        query_vector: The query embedding vector (1024-dim).
        top_k: Number of results to return.

    Returns:
        List of dicts, each containing the payload fields plus a 'score' field.
        Sorted by descending similarity score.

    Raises:
        ConnectionError: If Qdrant is not reachable.
    """
    client = _get_client()

    results = client.query_points(
        collection_name=COLLECTION_NAME,
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


def get_point_count() -> int:
    """Return the total number of points in the nyaya_corpus collection.

    Raises:
        ConnectionError: If Qdrant is not reachable.
    """
    client = _get_client()

    info = client.get_collection(collection_name=COLLECTION_NAME)
    return info.points_count or 0
