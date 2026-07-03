"""Nyaya AI — Statutory Corpus Ingestion Script.

Ingests Indian legal Acts from HuggingFace datasets into the nyaya_corpus
Qdrant collection. This is the first step before using query.py for
Mode 2 (Legal Intelligence Chat).

Usage:
    docker compose up -d        # Start Qdrant
    python ingest.py            # Run ingestion

Flow:
    1. Connect to Qdrant (fail fast if down)
    2. Create nyaya_corpus collection (idempotent)
    3. Load mratanusarkar/Indian-Laws (primary, pre-sectioned)
    4. Load geekyrakshit/indian-legal-acts (secondary, raw text, dedup-filtered)
    5. Embed all chunks with BGE-M3
    6. Upsert to Qdrant
    7. Print summary
"""

from __future__ import annotations

import sys
import time

from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.table import Table

from nyaya_ai.config import COLLECTION_NAME, EMBEDDING_DIM
from nyaya_ai.ingest.dedup import DedupRegistry
from nyaya_ai.ingest.loaders import load_geekyrakshit, load_mratanusarkar
from nyaya_ai.retrieval.embedder import Embedder
from nyaya_ai.store.qdrant import (
    create_collection,
    get_point_count,
    upsert_chunks,
)

console = Console()

EMBED_BATCH_SIZE = 64
UPSERT_BATCH_SIZE = 100


def main() -> None:
    """Run the full ingestion pipeline."""
    start_time = time.time()

    console.print(
        Panel(
            "[bold white]Nyaya AI — Statutory Corpus Ingestion[/]\n"
            "Ingesting Indian legal Acts into the vector store.",
            border_style="blue",
        )
    )

    # ------------------------------------------------------------------
    # Step 1: Connect to Qdrant
    # ------------------------------------------------------------------
    console.print("\n[bold]Step 1:[/] Connecting to Qdrant...")
    try:
        create_collection()
    except ConnectionError as e:
        console.print(f"\n[red bold]ERROR:[/] {e}")
        console.print(
            "\n[yellow]Make sure Qdrant is running:[/]\n"
            "  docker compose up -d\n"
        )
        sys.exit(1)

    # ------------------------------------------------------------------
    # Step 2: Load datasets with dedup
    # ------------------------------------------------------------------
    console.print("\n[bold]Step 2:[/] Loading datasets...\n")
    registry = DedupRegistry()

    # Primary dataset — pre-sectioned, registers in dedup
    primary_chunks = load_mratanusarkar(registry)

    # Secondary dataset — raw text, chunked, dedup-filtered
    secondary_chunks = load_geekyrakshit(registry)

    # Combine
    all_chunks = primary_chunks + secondary_chunks

    if not all_chunks:
        console.print("\n[red bold]No chunks loaded. Nothing to ingest.[/]")
        sys.exit(1)

    # Collect unique Act names for the summary
    act_names = set(c.act_name for c in all_chunks)

    console.print(
        f"\n[bold green]Total:[/] {len(all_chunks)} sections from "
        f"{len(act_names)} Acts | {registry.count} unique (act, section) pairs"
    )

    # ------------------------------------------------------------------
    # Step 3: Embed all chunks
    # ------------------------------------------------------------------
    console.print("\n[bold]Step 3:[/] Embedding chunks with BGE-M3...\n")
    embedder = Embedder()

    all_vectors: list[list[float]] = []
    texts = [c.text for c in all_chunks]

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(
            "Embedding...", total=len(texts)
        )

        for i in range(0, len(texts), EMBED_BATCH_SIZE):
            batch = texts[i : i + EMBED_BATCH_SIZE]
            batch_vectors = embedder.embed_documents(batch)
            all_vectors.extend(batch_vectors)
            progress.update(task, advance=len(batch))

    console.print(f"[green]  Embedded {len(all_vectors)} chunks.[/]")

    # ------------------------------------------------------------------
    # Step 4: Upsert to Qdrant
    # ------------------------------------------------------------------
    console.print("\n[bold]Step 4:[/] Upserting to Qdrant...\n")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(
            "Upserting...", total=len(all_chunks)
        )

        for i in range(0, len(all_chunks), UPSERT_BATCH_SIZE):
            batch_chunks = all_chunks[i : i + UPSERT_BATCH_SIZE]
            batch_vectors = all_vectors[i : i + UPSERT_BATCH_SIZE]
            upsert_chunks(batch_chunks, batch_vectors)
            progress.update(task, advance=len(batch_chunks))

    # ------------------------------------------------------------------
    # Step 5: Summary
    # ------------------------------------------------------------------
    elapsed = time.time() - start_time
    point_count = get_point_count()

    table = Table(title="Ingestion Summary", border_style="green")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Acts ingested", str(len(act_names)))
    table.add_row("Sections indexed", str(len(all_chunks)))
    table.add_row("  — from mratanusarkar", str(len(primary_chunks)))
    table.add_row("  — from geekyrakshit", str(len(secondary_chunks)))
    table.add_row("Unique (act, section) pairs", str(registry.count))
    table.add_row("Total points in Qdrant", str(point_count))
    table.add_row("Embedding dimension", str(EMBEDDING_DIM))
    table.add_row("Collection", COLLECTION_NAME)
    table.add_row("Time taken", f"{elapsed:.1f}s")

    console.print()
    console.print(table)
    console.print(
        f"\n[bold green]✓[/] Ingestion complete. "
        f"Run [bold]python query.py[/] to start chatting.\n"
    )


if __name__ == "__main__":
    main()
