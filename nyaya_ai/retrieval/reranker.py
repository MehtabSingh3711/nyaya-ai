"""Cross-encoder reranker for Nyaya AI (ADR-002, ADR-011).

Loads bge-reranker-v2-m3 as a cross-encoder that reads the full
(query, candidate) pair jointly. This is significantly more accurate
than comparing pre-computed embeddings, and is the key to filtering
out false-positive-adjacent noise (e.g., "Hire Purchase Act" matching
instead of the actual relevant statute).

Pipeline position:
    Hybrid search (dense + sparse, RRF) → top-20 candidates
    → Reranker (this module) → top-5 reranked candidates
    → LLM cascade
"""

from __future__ import annotations

from rich.console import Console

from nyaya_ai.config import RERANKER_MODEL

console = Console()


class Reranker:
    """Cross-encoder reranker using bge-reranker-v2-m3.

    Loads the model on first instantiation. Downloads ~560 MB on first run
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
        from sentence_transformers import CrossEncoder

        console.print(
            f"[bold blue]Loading reranker: {RERANKER_MODEL}...[/]\n"
            f"  (First run downloads model — cached for future runs)"
        )
        self._model = CrossEncoder(RERANKER_MODEL)
        console.print("[green]  Reranker loaded.[/]")

    def rerank(
        self,
        query: str,
        candidates: list[dict],
        top_k: int = 5,
        text_key: str = "text",
    ) -> list[dict]:
        """Rerank candidates using cross-encoder scoring.

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

        # Build (query, candidate_text) pairs for cross-encoder
        pairs = []
        for cand in candidates:
            cand_text = cand.get(text_key, "")
            # Include act_name and section_number for richer context
            act = cand.get("act_name", "")
            section = cand.get("section_number", "")
            prefix = f"{act} Section {section}: " if act else ""
            pairs.append((query, f"{prefix}{cand_text}"))

        # Score all pairs
        scores = self._model.predict(pairs)

        # Attach rerank_score to each candidate
        scored_candidates = []
        for cand, score in zip(candidates, scores):
            enriched = dict(cand)
            enriched["rerank_score"] = float(score)
            scored_candidates.append(enriched)

        # Sort by rerank_score descending, take top_k
        scored_candidates.sort(key=lambda x: x["rerank_score"], reverse=True)
        return scored_candidates[:top_k]
