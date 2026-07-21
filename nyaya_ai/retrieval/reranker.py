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
    """Cross-encoder reranker using Jina Reranker Cloud API (or local ONNX fallback).

    If JINA_API_KEY is present in config, reranking is executed on Jina's cloud endpoints
    for high speed and zero local memory consumption. If absent or offline, falls back
    to running the local cross-encoder model via ONNX.
    """

    def __init__(self) -> None:
        self._model = None
        if JINA_API_KEY:
            console.print("[green]Jina Reranker Cloud API initialized (Online Mode).[/]")
        else:
            console.print("[yellow]JINA_API_KEY not configured. Running local ONNX Reranker.[/]")

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
        """Rerank candidates using Jina Cloud Reranker or local fallback.

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

        scores = []
        if JINA_API_KEY:
            try:
                import requests
                import time
                import random
                url = "https://api.jina.ai/v1/rerank"
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {JINA_API_KEY}"
                }
                payload = {
                    "model": "jina-reranker-v1-turbo-en",
                    "query": query,
                    "documents": prefixed_texts,
                    "top_n": len(prefixed_texts)
                }
                
                response = None
                for attempt in range(4):
                    try:
                        response = requests.post(url, json=payload, headers=headers, timeout=5.0)
                        if response.status_code == 429:
                            # 429 rate limit hit, sleep with jitter and retry
                            sleep_dur = 1.0 + attempt * 1.0 + random.random()
                            time.sleep(sleep_dur)
                            continue
                        response.raise_for_status()
                        break
                    except (requests.RequestException, Exception) as req_err:
                        if attempt == 3:
                            raise req_err
                        time.sleep(1.0 + random.random())
                
                # Jina API returns results list ordered by relevance
                results = response.json().get("results", [])
                scores = [0.0] * len(prefixed_texts)
                for item in results:
                    scores[item["index"]] = float(item["relevance_score"])
            except Exception as e:
                console.print(f"[red][Warning] Jina API Reranking failed: {e}. Falling back to local ONNX.[/]")
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
