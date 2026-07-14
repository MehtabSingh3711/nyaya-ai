"""Nyaya AI — Legal Intelligence Chat (Mode 2 REPL).

Interactive terminal chat against the statutory corpus in Qdrant.
Type a legal question, get a cited answer backed by Indian law.

Pipeline:
    1. Embed query (BGE-M3 dense + sparse)
    2. Hybrid search (dense + sparse, RRF fusion) → top-20 candidates
    3. Cross-encoder rerank (bge-reranker-v2-m3) → top-5
    4. LLM cascade → cited answer

Usage:
    python ingest.py           # Run once to populate the corpus
    python query.py            # Start the chat REPL

Requires:
    - Qdrant data at ./qdrant_data (populated via ingest.py)
    - API keys in .env (GROQ_API_KEY, etc.)
"""

from __future__ import annotations

import sys
import time

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
from rich.theme import Theme

from nyaya_ai.config import COLLECTION_NAME, RERANK_CANDIDATES, FINAL_TOP_K
from nyaya_ai.llm.cascade import cascade_query
from nyaya_ai.retrieval.embedder import Embedder
from nyaya_ai.retrieval.reranker import Reranker
from nyaya_ai.store.qdrant import get_point_count, search

# Custom theme for consistent styling
theme = Theme(
    {
        "answer": "white",
        "citation.act": "cyan bold",
        "citation.section": "cyan",
        "citation.quote": "italic dim",
        "confidence.high": "green bold",
        "confidence.mid": "yellow bold",
        "confidence.low": "red bold",
        "refuse": "yellow",
    }
)

console = Console(theme=theme)


def _print_banner() -> None:
    """Print the Nyaya AI welcome banner."""
    banner = Text()
    banner.append("⚖️  Nyaya AI", style="bold white")
    banner.append(" — Legal Intelligence Chat\n", style="dim")
    banner.append("   Know what you sign.\n\n", style="italic cyan")
    banner.append("   Corpus: ", style="dim")
    banner.append(COLLECTION_NAME, style="cyan")

    try:
        count = get_point_count()
        banner.append(f" ({count:,} sections indexed)\n", style="dim")
    except ConnectionError:
        banner.append(" (could not reach Qdrant)\n", style="red")

    banner.append("   Pipeline: ", style="dim")
    banner.append("hybrid (dense+sparse) → rerank → cascade\n", style="cyan")

    banner.append("\n   Type your legal question. Type ", style="dim")
    banner.append("quit", style="bold")
    banner.append(" to exit.", style="dim")

    console.print(Panel(banner, border_style="blue", padding=(1, 2)))


def _display_answer(result, context_chunks: list[dict]) -> None:
    """Display a CitedAnswer using rich formatting."""
    if not result.can_answer:
        _display_refuse(result, context_chunks)
        return

    # -- Answer panel --
    console.print()
    console.print(
        Panel(
            result.answer,
            title="[bold white]Answer[/]",
            border_style="green",
            padding=(1, 2),
        )
    )

    # -- Citations --
    if result.citations:
        console.print()
        console.print("[bold]📎 Citations:[/]")
        for i, cit in enumerate(result.citations, 1):
            console.print(
                f"\n  [citation.act][{i}] {cit.act_name}[/], "
                f"[citation.section]§{cit.section}[/]"
            )
            # Wrap the quote in dimmed italic
            quote_lines = cit.quote.strip().split("\n")
            for line in quote_lines:
                console.print(f"      [citation.quote]\"{line}\"[/]")

    # -- Confidence --
    console.print()
    conf = result.confidence
    if conf >= 0.8:
        style = "confidence.high"
    elif conf >= 0.6:
        style = "confidence.mid"
    else:
        style = "confidence.low"
    console.print(f"  🎯 Confidence: [{style}]{conf:.2f}[/]")
    console.print()


def _display_refuse(result, context_chunks: list[dict]) -> None:
    """Display a cite-or-refuse response."""
    console.print()
    console.print(
        Panel(
            f"[refuse]{result.answer}[/]",
            title="[yellow bold]⚠ Insufficient Information[/]",
            border_style="yellow",
            padding=(1, 2),
        )
    )

    # Show what was retrieved so the user can see what the system found
    if context_chunks:
        console.print()
        console.print("[dim]Here's what was found in the corpus:[/]")
        for i, chunk in enumerate(context_chunks[:3], 1):
            act = chunk.get("act_name", "Unknown")
            sec = chunk.get("section_number", "?")
            score = chunk.get("score", 0.0)
            text_preview = chunk.get("text", "")[:200]
            console.print(
                f"\n  [dim][{i}] {act}, §{sec} (score: {score:.2f})[/]"
            )
            console.print(f"      [dim italic]{text_preview}...[/]")

    console.print()
    conf = result.confidence
    console.print(f"  🎯 Confidence: [confidence.low]{conf:.2f}[/]")
    console.print()


def main() -> None:
    """Run the Mode 2 Legal Intelligence Chat REPL."""

    # ------------------------------------------------------------------
    # Startup: connect to services
    # ------------------------------------------------------------------
    console.print("\n[dim]Connecting to services...[/]")

    # Check Qdrant
    try:
        point_count = get_point_count()
        if point_count == 0:
            console.print(
                "\n[yellow bold]WARNING:[/] nyaya_corpus is empty. "
                "Run [bold]python ingest.py[/] first.\n"
            )
            sys.exit(1)
    except ConnectionError as e:
        console.print(f"\n[red bold]ERROR:[/] {e}")
        console.print("[yellow]Start Qdrant with:[/] docker compose up -d\n")
        sys.exit(1)

    # Load embedder (downloads BGE-M3 on first run)
    try:
        embedder = Embedder()
    except Exception as e:
        console.print(f"\n[red bold]ERROR:[/] Failed to load embedding model: {e}")
        sys.exit(1)

    # Load reranker (downloads bge-reranker-v2-m3 on first run)
    try:
        reranker = Reranker()
    except Exception as e:
        console.print(f"\n[red bold]ERROR:[/] Failed to load reranker: {e}")
        sys.exit(1)

    # ------------------------------------------------------------------
    # Banner
    # ------------------------------------------------------------------
    console.print()
    _print_banner()
    console.print()

    # ------------------------------------------------------------------
    # REPL loop
    # ------------------------------------------------------------------
    while True:
        try:
            question = console.input("[bold cyan]nyaya>[/] ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n\n[dim]Goodbye.[/]\n")
            break

        # Empty input — just prompt again
        if not question:
            continue

        # Exit commands
        if question.lower() in ("quit", "exit", "q"):
            console.print("\n[dim]Goodbye.[/]\n")
            break

        # Process the question
        console.print("[dim]  Searching corpus (hybrid)...[/]")
        start = time.time()

        # Step 1: Embed the question (dense + sparse)
        query_hybrid = embedder.embed_query_hybrid(question)

        # Step 2: Hybrid search (dense + sparse, RRF fusion) → top-20
        candidates = search(
            query_vector=query_hybrid.dense,
            sparse_vector=query_hybrid.sparse,
            top_k=RERANK_CANDIDATES,
        )

        if not candidates:
            console.print(
                Panel(
                    "[yellow]No relevant sections found in the corpus. "
                    "Try rephrasing your question.[/]",
                    title="[yellow bold]No Results[/]",
                    border_style="yellow",
                )
            )
            continue

        # Step 3: Cross-encoder rerank → top-5
        console.print("[dim]  Reranking candidates...[/]")
        context_chunks = reranker.rerank(
            query=question,
            candidates=candidates,
            top_k=FINAL_TOP_K,
        )

        # Step 4: LLM cascade
        console.print("[dim]  Generating answer...[/]")
        result = cascade_query(question, context_chunks)

        elapsed = time.time() - start
        console.print(f"[dim]  ({elapsed:.1f}s)[/]")

        # Step 5: Display
        _display_answer(result, context_chunks)


if __name__ == "__main__":
    main()
