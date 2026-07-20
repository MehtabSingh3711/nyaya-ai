"""Nyaya AI — Case Law Precedents Ingestion Script (Local Edition).

Reads the corrected and verified 100 cases manifest from `docs/data/precedent_cases_manifest.md`
locally, parses it into structured metadata, generates dense and sparse embeddings via BGE-M3,
and indexes them into the local 'nyaya_precedents' Qdrant collection.

Usage:
    python ingest_precedents.py
"""

from __future__ import annotations

import os
import re
import sys
import uuid
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    MofNCompleteColumn,
    TimeElapsedColumn,
)
from rich.table import Table

from nyaya_ai.config import PRECEDENTS_COLLECTION_NAME
from nyaya_ai.retrieval.embedder import Embedder
from nyaya_ai.schemas import PrecedentChunk
from nyaya_ai.store.qdrant import create_collection, upsert_chunks, get_point_count, _get_client

console = Console()


def parse_manifest_file(filepath: Path) -> list[PrecedentChunk]:
    """Parse the markdown table in the manifest file to extract PrecedentChunk records."""
    if not filepath.exists():
        console.print(f"[red]Error: Precedent cases manifest not found at {filepath}[/]")
        sys.exit(1)

    console.print(f"[blue]Reading corrected precedents from {filepath}...[/]")
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    chunks = []

    for line_num, line in enumerate(lines, 1):
        line = line.strip()
        if not line.startswith("|") or not line.endswith("|"):
            continue

        parts = [p.strip() for p in line.split("|")]
        # Ensure we have enough columns and the first column is a case index digit
        if len(parts) < 6 or not parts[1].isdigit():
            continue

        case_and_citation = parts[2]
        category = parts[3]
        key_issue = parts[4]
        core_holding = parts[5]

        # Extract case name from bold tags
        name_match = re.search(r"\*\*(.*?)\*\*", case_and_citation)
        if name_match:
            case_name = name_match.group(1).strip()
            citation = case_and_citation.replace(f"**{case_name}**", "").strip()
        else:
            case_name = case_and_citation
            citation = "Supreme Court of India"

        # Unified text layout for embedding search
        unified_text = (
            f"Case Name: {case_name}\n"
            f"Citation: {citation}\n"
            f"Category: {category}\n"
            f"Key Legal Issue: {key_issue}\n"
            f"Core Judicial Holding: {core_holding}"
        )

        chunk = PrecedentChunk(
            case_name=case_name,
            citation=citation,
            category=category,
            key_issue=key_issue,
            core_holding=core_holding,
            text=unified_text,
            source=filepath.name,
            version="v1"
        )
        chunks.append(chunk)

    console.print(f"[green]✓ Parsed {len(chunks)} corrected precedents successfully![/]")
    return chunks


def main() -> None:
    manifest_path = Path("docs/data/precedent_cases_manifest.md")
    chunks = parse_manifest_file(manifest_path)

    if not chunks:
        console.print("[red]No precedents parsed. Exiting.[/]")
        return

    # 1. Connect and initialize Qdrant precedents collection
    console.print(f"[blue]Initializing Qdrant collection: {PRECEDENTS_COLLECTION_NAME}...[/]")
    try:
        client = _get_client()
        existing = [c.name for c in client.get_collections().collections]
        if PRECEDENTS_COLLECTION_NAME in existing:
            console.print(f"[yellow]Collection '{PRECEDENTS_COLLECTION_NAME}' already exists. Recreating...[/]")
            client.delete_collection(PRECEDENTS_COLLECTION_NAME)
        create_collection(PRECEDENTS_COLLECTION_NAME)
    except Exception as e:
        console.print(f"[red]Failed to connect to Qdrant or create collection: {e}[/]")
        sys.exit(1)

    # 2. Instantiate hybrid embedder
    try:
        embedder = Embedder()
    except Exception as e:
        console.print(f"[red]Failed to initialize embedding model: {e}[/]")
        sys.exit(1)

    # 3. Batch embed documents using hybrid method (dense + sparse)
    texts = [c.text for c in chunks]
    console.print(f"[blue]Generating hybrid BGE-M3 embeddings for {len(chunks)} precedents...[/]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        embed_task = progress.add_task("[cyan]Embedding precedents...", total=len(chunks))

        dense_vectors = []
        sparse_vectors = []

        batch_size = 32
        for i in range(0, len(chunks), batch_size):
            batch_texts = texts[i : i + batch_size]
            result = embedder.embed_documents_hybrid(batch_texts, batch_size=batch_size)
            dense_vectors.extend(result.dense)
            sparse_vectors.extend(result.sparse)
            progress.update(embed_task, advance=len(batch_texts))

    # 4. Upsert to Qdrant Local
    console.print(f"[blue]Upserting to Qdrant collection '{PRECEDENTS_COLLECTION_NAME}'...[/]")
    try:
        upsert_chunks(
            chunks=chunks,
            vectors=dense_vectors,
            collection_name=PRECEDENTS_COLLECTION_NAME,
            sparse_vectors=sparse_vectors,
        )
    except Exception as e:
        console.print(f"[red]Failed to upsert to Qdrant: {e}[/]")
        sys.exit(1)

    # 5. Print Ingestion Table Summary
    qdrant_points = get_point_count(PRECEDENTS_COLLECTION_NAME)

    table = Table(title="Precedents Ingestion Run Summary", show_header=True, header_style="bold magenta")
    table.add_column("Precedents Processed", justify="right")
    table.add_column("Qdrant Collection Target", justify="left")
    table.add_column("Total Active Points", justify="right", style="green")
    table.add_row(str(len(chunks)), PRECEDENTS_COLLECTION_NAME, str(qdrant_points))

    console.print("\n")
    console.print(Panel(table, border_style="green", title="[bold green]Ingestion Complete[/]"))


if __name__ == "__main__":
    main()
