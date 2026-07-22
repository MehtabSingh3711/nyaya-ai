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
        from nyaya_ai.config import REMOTE_EMBEDDING_URL, EMBEDDING_MODEL
        self._remote_url = REMOTE_EMBEDDING_URL.rstrip('/') if REMOTE_EMBEDDING_URL else None
        self._model = None

        if self._remote_url:
            console.print(f"[bold green]Using Remote GPU Embedding Service: {self._remote_url}[/]")
        else:
            from FlagEmbedding import BGEM3FlagModel
            console.print(
                f"[bold blue]Loading embedding model: {EMBEDDING_MODEL}...[/]\n"
                f"  (First run downloads ~2.3 GB — cached for future runs)"
            )
            self._model = BGEM3FlagModel(EMBEDDING_MODEL, use_fp16=use_fp16)
            console.print(f"[green]  Model loaded (dense + sparse support).[/]")

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if self._remote_url:
            import requests
            resp = requests.post(f"{self._remote_url}/embed_documents_hybrid", json={"texts": texts})
            resp.raise_for_status()
            return resp.json()["dense"]

        output = self._model.encode(
            texts,
            batch_size=32,
            return_dense=True,
            return_sparse=False,
            return_colbert_vecs=False,
            verbose=False,
        )
        return output["dense_vecs"].tolist()

    def embed_query(self, text: str) -> list[float]:
        if self._remote_url:
            import requests
            resp = requests.post(f"{self._remote_url}/embed_query_hybrid", json={"text": text})
            resp.raise_for_status()
            return resp.json()["dense"]

        output = self._model.encode(
            [text],
            batch_size=1,
            return_dense=True,
            return_sparse=False,
            return_colbert_vecs=False,
            verbose=False,
        )
        return output["dense_vecs"][0].tolist()

    def embed_documents_hybrid(self, texts: list[str], batch_size: int = 32) -> HybridVectors:
        if self._remote_url:
            import requests
            resp = requests.post(f"{self._remote_url}/embed_documents_hybrid", json={"texts": texts, "batch_size": batch_size})
            resp.raise_for_status()
            data = resp.json()
            # Convert sparse dictionary keys back to ints
            sparse_converted = [{int(k): float(v) for k, v in d.items()} for d in data["sparse"]]
            return HybridVectors(dense=data["dense"], sparse=sparse_converted)

        output = self._model.encode(
            texts,
            batch_size=batch_size,
            return_dense=True,
            return_sparse=True,
            return_colbert_vecs=False,
            verbose=False,
        )

        dense_vecs = output["dense_vecs"].tolist()

        # Convert lexical_weights to {int_token_id: float_weight} dicts
        sparse_vecs = []
        for weights_dict in output["lexical_weights"]:
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
        if self._remote_url:
            import requests
            resp = requests.post(f"{self._remote_url}/embed_query_hybrid", json={"text": text}, timeout=30.0)
            resp.raise_for_status()
            data = resp.json()
            sparse_converted = {int(k): float(v) for k, v in data["sparse"].items()}
            return HybridQueryVectors(
                dense=data["dense"],
                sparse=sparse_converted,
            )

        result = self.embed_documents_hybrid([text], batch_size=1)
        return HybridQueryVectors(
            dense=result.dense[0],
            sparse=result.sparse[0],
        )
