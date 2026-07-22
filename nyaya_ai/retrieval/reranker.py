"""Cross-encoder reranker for Nyaya AI (ADR-002, ADR-011).

Loads jina-reranker-v1-turbo-en as an ONNX cross-encoder that reads the full
(query, candidate) pair jointly. This is significantly more accurate
than comparing pre-computed embeddings, and is the key to filtering
out false-positive-adjacent noise (e.g., "Hire Purchase Act" matching
instead of the actual relevant statute).

We use jinaai/jina-reranker-v1-turbo-en (150MB, Apache 2.0). It provides
a native 8K context length (compared to BGE's 512 tokens), preventing
truncation of long legal sections, while executing in milliseconds on local CPU
using FastEmbed's ONNX runtime.

Pipeline position:
    Hybrid search (dense + sparse, RRF) → top-20 candidates
    → Reranker (this module) → top-5 reranked candidates
    └─ LLM cascade
"""

from __future__ import annotations

from rich.console import Console

from nyaya_ai.config import RERANKER_MODEL, JINA_API_KEY

console = Console()


class Reranker:
    """Cross-encoder reranker using Kaggle Remote GPU microservice or local ONNX fallback."""

    def __init__(self) -> None:
        from nyaya_ai.config import REMOTE_EMBEDDING_URL
        self._remote_url = REMOTE_EMBEDDING_URL.rstrip('/') if REMOTE_EMBEDDING_URL else None
        self._model = None

        if self._remote_url:
            console.print(f"[bold green]Using Remote GPU Reranker Microservice: {self._remote_url}[/]")
        else:
            console.print("[yellow]REMOTE_EMBEDDING_URL not set. Running local ONNX Reranker.[/]")

    def _score_locally(self, query: str, prefixed_texts: list[str]) -> list[float]:
        """Lazy-loads and executes local ONNX cross-encoder scoring."""
        if self._model is None:
            from fastembed.rerank.cross_encoder import TextCrossEncoder

            console.print(
                f"[bold blue]Loading local ONNX reranker: {RERANKER_MODEL}...[/]\n"
                f"  (First run downloads model — cached for future runs)"
            )
            self._model = TextCrossEncoder(model_name=RERANKER_MODEL)
            console.print("[green]  ONNX Reranker loaded.[/]")
        return list(self._model.rerank(query=query, documents=prefixed_texts))

    def rerank(
        self,
        query: str,
        candidates: list[dict],
        top_k: int = 5,
        text_key: str = "text",
    ) -> list[dict]:
        """Rerank candidates using Kaggle GPU Microservice or local ONNX fallback.

        Each candidate dict must contain a text field (default key: "text")
        that will be paired with the query for cross-encoder scoring.
        """
        if not candidates:
            return []

        # Build prefixed document texts to provide richer context to cross-encoder
        prefixed_texts = []
        for cand in candidates:
            cand_text = cand.get(text_key, "")
            act = cand.get("act_name", "")
            section = cand.get("section_number", "")
            prefix = f"{act} Section {section}: " if act else ""
            prefixed_texts.append(f"{prefix}{cand_text}")

        scores = []
        if self._remote_url:
            try:
                import requests
                url = f"{self._remote_url}/rerank"
                payload = {
                    "query": query,
                    "documents": prefixed_texts,
                    "top_n": len(prefixed_texts)
                }
                resp = requests.post(url, json=payload, timeout=30.0)
                resp.raise_for_status()
                results = resp.json().get("results", [])
                scores = [0.0] * len(prefixed_texts)
                for item in results:
                    scores[item["index"]] = float(item["relevance_score"])
            except Exception as remote_err:
                console.print(f"[red][Warning] Remote GPU Rerank failed: {remote_err}. Falling back to local ONNX.[/]")
                scores = self._score_locally(query, prefixed_texts)
        else:
            scores = self._score_locally(query, prefixed_texts)

        # Map scores back to original candidate dicts
        scored_candidates = []
        for cand, score in zip(candidates, scores):
            enriched = dict(cand)
            enriched["rerank_score"] = float(score)
            scored_candidates.append(enriched)

        # Sort by rerank_score descending, take top_k
        scored_candidates.sort(key=lambda x: x["rerank_score"], reverse=True)
        return scored_candidates[:top_k]
