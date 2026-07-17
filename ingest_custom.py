"""Nyaya AI — Helper script to ingest custom JSON-formatted Acts into Qdrant.

Usage:
    python ingest_custom.py path/to/your_act.json
"""

import json
import os
import sys
from pathlib import Path

from rich.console import Console

from nyaya_ai.config import COLLECTION_NAME
from nyaya_ai.retrieval.embedder import Embedder
from nyaya_ai.schemas import CorpusChunk
from nyaya_ai.store.qdrant import upsert_chunks, get_point_count

console = Console()


def main():
    if len(sys.argv) < 2:
        console.print("[red bold]Error:[/] Please provide the path to your JSON file.")
        console.print("Usage: python ingest_custom.py path/to/your_act.json")
        sys.exit(1)

    json_path = Path(sys.argv[1])
    if not json_path.exists():
        console.print(f"[red bold]Error:[/] File not found: {json_path}")
        sys.exit(1)

    console.print(f"[bold blue]Loading custom Act data from:[/] {json_path}")
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
    except Exception as e:
        console.print(f"[red bold]Failed to parse JSON:[/] {e}")
        sys.exit(1)

    if not isinstance(raw_data, list):
        console.print("[red bold]Error:[/] JSON file must contain a list of section objects.")
        sys.exit(1)

    from datetime import datetime
    current_date = datetime.now().strftime("%Y-%m-%d")

    chunks = []
    for idx, item in enumerate(raw_data, 1):
        if not all(k in item for k in ("act_name", "section_number", "text")):
            console.print(f"[yellow]Skipping item #{idx}: Missing required fields ('act_name', 'section_number', 'text')[/]")
            continue
        
        chunk = CorpusChunk(
            act_name=item["act_name"].strip(),
            section_number=str(item["section_number"]).strip(),
            section_title=item.get("section_title", "").strip() or None,
            chapter=item.get("chapter", "").strip() or None,
            text=item["text"].strip(),
            source=json_path.name,
            version="2023-reforms",
            amendment_status="original",
            last_verified_source="Gazette of India",
            last_verified_date=current_date
        )
        chunks.append(chunk)

    if not chunks:
        console.print("[red bold]No valid sections found in JSON. Ingestion aborted.[/]")
        sys.exit(1)

    console.print(f"[green]✓ Loaded {len(chunks)} sections.[/]")
    
    # Initialize embedder and compute hybrid vectors
    console.print("\n[bold]Step 1:[/] Initializing Embedder (BGE-M3)...")
    embedder = Embedder()
    
    console.print(f"\n[bold]Step 2:[/] Embedding {len(chunks)} sections (hybrid: dense + sparse)...")
    texts = [c.text for c in chunks]
    hybrid = embedder.embed_documents_hybrid(texts, batch_size=32)
    
    console.print("\n[bold]Step 3:[/] Upserting points to Qdrant...")
    upsert_chunks(
        chunks=chunks,
        dense_vectors=hybrid.dense,
        sparse_vectors=hybrid.sparse
    )
    
    console.print(f"\n[bold green]Success![/] Index complete. Total database points: [cyan]{get_point_count()}[/]")


if __name__ == "__main__":
    main()
