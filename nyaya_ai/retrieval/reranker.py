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

from nyaya_ai.config import RERANKER_MODEL

console = Console()


class Reranker:
    """Cross-encoder reranker using jina-reranker-v1-turbo-en.

    Loads the model on first instantiation. Downloads ~150 MB on first run
    (cached by HuggingFace).

    Usage:
        reranker = Reranker()
        reranked = reranker.rerank(
            query="non-compete clause enforceability",
            candidates=[{"text": "...", "score": 0.8, ...}, ...],
            top_k=5,
        )
    """

    def __init__(self) -> None:
        from fastembed.rerank.cross_encoder import TextCrossEncoder

        console.print(
            f"[bold blue]Loading ONNX reranker: {RERANKER_MODEL}...[/]\n"
            f"  (First run downloads model — cached for future runs)"
        )
        self._model = TextCrossEncoder(model_name=RERANKER_MODEL)
        console.print("[green]  ONNX Reranker loaded.[/]")

    def rerank(
        self,
        query: str,
        candidates: list[dict],
        top_k: int = 5,
        text_key: str = "text",
    ) -> list[dict]:
        """Rerank candidates using cross-encoder scoring via FastEmbed (ONNX).

        Each candidate dict must contain a text field (default key: "text")
        that will be paired with the query for cross-encoder scoring.

        Args:
            query: The search query string.
            candidates: List of candidate dicts from hybrid search.
                        Each must have a ``text_key`` field.
            top_k: Number of top results to return after reranking.
            text_key: Key in candidate dicts containing the text to score.

        Returns:
            Top-k candidates sorted by cross-encoder score (descending).
            Each dict gets an added ``rerank_score`` field and retains
            the original ``score`` field from retrieval.
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

        # Score using FastEmbed's ONNX reranker (returns float scores in original order)
        scores = list(self._model.rerank(query=query, documents=prefixed_texts))

        # Map scores back to original candidate dicts
        scored_candidates = []
        for cand, score in zip(candidates, scores):
            enriched = dict(cand)
            enriched["rerank_score"] = float(score)
            scored_candidates.append(enriched)

        # Sort by rerank_score descending, take top_k
        scored_candidates.sort(key=lambda x: x["rerank_score"], reverse=True)
        return scored_candidates[:top_k]
