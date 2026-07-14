"""BGE-M3 embedding wrapper for Nyaya AI (ADR-002, ADR-011).

Loads BAAI/bge-m3 via FlagEmbedding's BGEM3FlagModel.
Produces BOTH dense (1024-dim) and sparse (lexical weight) vectors
in a single forward pass — used for hybrid retrieval in Qdrant.

Dense vectors → cosine similarity search
Sparse vectors → BM25-equivalent lexical matching (Qdrant SparseVector)
"""

from __future__ import annotations

from typing import NamedTuple

from rich.console import Console

from nyaya_ai.config import EMBEDDING_MODEL

console = Console()


class HybridVectors(NamedTuple):
    """Container for dense + sparse vector outputs from BGE-M3."""

    dense: list[list[float]]
    sparse: list[dict[int, float]]  # [{token_id: weight}, ...]


class HybridQueryVectors(NamedTuple):
    """Container for a single query's dense + sparse vectors."""

    dense: list[float]
    sparse: dict[int, float]  # {token_id: weight}


class Embedder:
    """BGE-M3 embedding model wrapper — dense + sparse hybrid.

    Loads the model on first instantiation via FlagEmbedding.
    Downloads ~2.3 GB on first run (cached by HuggingFace).

    Usage:
        embedder = Embedder()

        # Dense only (backward compatible)
        vectors = embedder.embed_documents(["text 1", "text 2"])
        query_vec = embedder.embed_query("what is section 27?")

        # Hybrid (dense + sparse)
        hybrid = embedder.embed_documents_hybrid(["text 1", "text 2"])
        query_hybrid = embedder.embed_query_hybrid("what is section 27?")
    """

    def __init__(self, use_fp16: bool = True) -> None:
        # pyrefly: ignore [missing-import]
        from FlagEmbedding import BGEM3FlagModel

        console.print(
            f"[bold blue]Loading embedding model: {EMBEDDING_MODEL}...[/]\n"
            f"  (First run downloads ~2.3 GB — cached for future runs)"
        )
        self._model = BGEM3FlagModel(EMBEDDING_MODEL, use_fp16=use_fp16)
        console.print(f"[green]  Model loaded (dense + sparse support).[/]")

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Batch embed document texts — dense vectors only (backward compatible).

        Args:
            texts: List of text strings to embed.

        Returns:
            List of 1024-dimensional normalized embedding vectors.
        """
        output = self._model.encode(
            texts,
            batch_size=32,
            return_dense=True,
            return_sparse=False,
            return_colbert_vecs=False,
        )
        return output["dense_vecs"].tolist()

    def embed_query(self, text: str) -> list[float]:
        """Embed a single query text — dense vector only (backward compatible).

        Args:
            text: The query string.

        Returns:
            A 1024-dimensional normalized embedding vector.
        """
        output = self._model.encode(
            [text],
            batch_size=1,
            return_dense=True,
            return_sparse=False,
            return_colbert_vecs=False,
        )
        return output["dense_vecs"][0].tolist()

    def embed_documents_hybrid(self, texts: list[str], batch_size: int = 32) -> HybridVectors:
        """Batch embed documents — both dense AND sparse vectors.

        One forward pass produces both vector types. This is the method
        used during ingestion to populate Qdrant with hybrid named vectors.

        Args:
            texts: List of text strings to embed.
            batch_size: Batch size for encoding.

        Returns:
            HybridVectors with .dense (list of 1024-dim vectors) and
            .sparse (list of {token_id: weight} dicts).
        """
        output = self._model.encode(
            texts,
            batch_size=batch_size,
            return_dense=True,
            return_sparse=True,
            return_colbert_vecs=False,
        )

        dense_vecs = output["dense_vecs"].tolist()

        # Convert lexical_weights to {int_token_id: float_weight} dicts
        sparse_vecs = []
        for weights_dict in output["lexical_weights"]:
            # BGE-M3 returns {token_str_or_id: weight}
            # Convert keys to int token IDs if they're strings
            converted = {}
            for key, value in weights_dict.items():
                if isinstance(key, str):
                    token_ids = self._model.tokenizer.convert_tokens_to_ids([key])
                    converted[token_ids[0]] = float(value)
                else:
                    converted[int(key)] = float(value)
            sparse_vecs.append(converted)

        return HybridVectors(dense=dense_vecs, sparse=sparse_vecs)

    def embed_query_hybrid(self, text: str) -> HybridQueryVectors:
        """Embed a single query — both dense AND sparse vectors.

        Used at search time to produce both vector types for hybrid retrieval.

        Args:
            text: The query string.

        Returns:
            HybridQueryVectors with .dense (1024-dim vector) and
            .sparse ({token_id: weight} dict).
        """
        result = self.embed_documents_hybrid([text], batch_size=1)
        return HybridQueryVectors(
            dense=result.dense[0],
            sparse=result.sparse[0],
        )
