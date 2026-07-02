"""BGE-M3 embedding wrapper for Nyaya AI (ADR-002).

Loads BAAI/bge-m3 via sentence-transformers once on init.
Provides batch embedding for ingestion and single-query embedding for search.
All embeddings are L2-normalized for cosine similarity.
"""

from __future__ import annotations

from rich.console import Console

from nyaya_ai.config import EMBEDDING_MODEL

console = Console()


class Embedder:
    """BGE-M3 embedding model wrapper.

    Loads the model on first instantiation. Downloads ~2.3 GB on first run
    (cached by HuggingFace in the default cache directory).

    Usage:
        embedder = Embedder()
        vectors = embedder.embed_documents(["text 1", "text 2"])
        query_vec = embedder.embed_query("what is section 27?")
    """

    def __init__(self) -> None:
        from sentence_transformers import SentenceTransformer

        console.print(
            f"[bold blue]Loading embedding model: {EMBEDDING_MODEL}...[/]\n"
            f"  (First run downloads ~2.3 GB — cached for future runs)"
        )
        self._model = SentenceTransformer(EMBEDDING_MODEL)
        console.print(f"[green]  Model loaded.[/]")

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Batch embed document texts for ingestion.

        Args:
            texts: List of text strings to embed.

        Returns:
            List of 1024-dimensional normalized embedding vectors.
        """
        embeddings = self._model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=len(texts) > 50,
            batch_size=32,
        )
        return embeddings.tolist()

    def embed_query(self, text: str) -> list[float]:
        """Embed a single query text for search.

        Args:
            text: The query string.

        Returns:
            A 1024-dimensional normalized embedding vector.
        """
        embedding = self._model.encode(
            text,
            normalize_embeddings=True,
        )
        return embedding.tolist()
