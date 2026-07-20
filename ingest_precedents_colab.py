"""Nyaya AI — Case Law Precedents Ingestion Script (Google Colab Edition).

This script is optimized to run on a Google Colab T4 GPU runtime.
It loads your corrected and verified 100 cases manifest from GitHub,
parses it into structured metadata, generates dense and sparse embeddings via BGE-M3,
and exports a Qdrant collection snapshot (.snapshot) containing the 100 real precedents.

Usage in Colab:
    Create a new code cell, paste this code, and run it.
"""

# Install dependencies if running in Colab
try:
    import google.colab
    IN_COLAB = True
    print("Installing dependencies in Google Colab...")
    !pip install -q qdrant-client FlagEmbedding rich
except ImportError:
    IN_COLAB = False
    print("Running in local python environment.")

import os
import re
import urllib.request
from pathlib import Path
import uuid

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

# Configure collection names and local path
PRECEDENTS_COLLECTION_NAME = "nyaya_precedents"
EMBEDDING_DIM = 1024
QDRANT_PATH = "./qdrant_precedents_temp"

# Raw GitHub URL to pull your newly committed cases manifest
GITHUB_MANIFEST_URL = "https://raw.githubusercontent.com/MehtabSingh3711/nyaya-ai/main/docs/data/precedent_cases_manifest.md"


def download_manifest() -> Path:
    """Download the precedents manifest from GitHub to Colab's workspace."""
    local_path = Path("precedent_cases_manifest_temp.md")
    console.print(f"[blue]Downloading verified precedents manifest from GitHub:\n  {GITHUB_MANIFEST_URL}[/]")
    urllib.request.urlretrieve(GITHUB_MANIFEST_URL, local_path)
    console.print(f"[green]✓ Manifest downloaded and saved to: {local_path}[/]")
    return local_path


def parse_manifest_file(filepath: Path) -> list[dict]:
    """Parse the markdown table in the manifest file to extract case dicts."""
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    cases = []

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

        cases.append({
            "case_name": case_name,
            "citation": citation,
            "category": category,
            "key_issue": key_issue,
            "core_holding": core_holding,
            "text": unified_text,
            "source": "precedent_cases_manifest.md",
            "version": "v1"
        })

    console.print(f"[green]✓ Parsed {len(cases)} corrected precedents from manifest.[/]")
    return cases


def main():
    # 1. Download Manifest
    manifest_file = download_manifest()
    cases = cases = parse_manifest_file(manifest_file)

    if not cases:
        console.print("[red]No cases parsed. Exiting.[/]")
        return

    # 2. Initialize Qdrant local client
    console.print(f"[blue]Initializing Qdrant client at local path: {QDRANT_PATH}...[/]")
    client = QdrantClient(path=QDRANT_PATH)

    # 3. Create collection with hybrid named-vector config
    existing = [c.name for c in client.get_collections().collections]
    if PRECEDENTS_COLLECTION_NAME in existing:
        console.print(f"[yellow]Collection '{PRECEDENTS_COLLECTION_NAME}' already exists. Recreating...[/]")
        client.delete_collection(PRECEDENTS_COLLECTION_NAME)

    client.create_collection(
        collection_name=PRECEDENTS_COLLECTION_NAME,
        vectors_config={
            "dense": qmodels.VectorParams(
                size=EMBEDDING_DIM,
                distance=qmodels.Distance.COSINE,
            ),
        },
        sparse_vectors_config={
            "sparse": qmodels.SparseVectorParams(),
        },
    )
    console.print(f"[green]✓ Created hybrid collection '{PRECEDENTS_COLLECTION_NAME}'.[/]")

    # 4. Load BGE-M3 on GPU
    console.print("[blue]Loading BGE-M3 on GPU (use_fp16=True)...[/]")
    from FlagEmbedding import BGEM3FlagModel
    # FlagEmbedding automatically picks CUDA if available
    embed_model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=True)
    console.print("[green]✓ BGE-M3 model loaded successfully.[/]")

    # 5. Embed text content
    texts = [c["text"] for c in cases]
    console.print(f"[blue]Embedding {len(cases)} verified cases on GPU (Batch size: 32)...[/]")
    
    output = embed_model.encode(
        texts,
        batch_size=32,
        return_dense=True,
        return_sparse=True,
        verbose=True
    )
    dense_vecs = output["dense_vecs"].tolist()

    # Convert sparse format
    sparse_vecs = []
    for weights_dict in output["lexical_weights"]:
        converted = {}
        for key, value in weights_dict.items():
            if isinstance(key, str):
                token_ids = embed_model.tokenizer.convert_tokens_to_ids([key])
                converted[token_ids[0]] = float(value)
            else:
                converted[int(key)] = float(value)
        sparse_vecs.append(converted)

    # 6. Upsert points
    points = []
    for i, case in enumerate(cases):
        vector_data = {
            "dense": dense_vecs[i],
            "sparse": qmodels.SparseVector(
                indices=list(sparse_vecs[i].keys()),
                values=list(sparse_vecs[i].values()),
            )
        }
        points.append(
            qmodels.PointStruct(
                id=str(uuid.uuid4()),
                vector=vector_data,
                payload=case
            )
        )

    console.print(f"[blue]Upserting {len(points)} points into Qdrant...[/]")
    client.upsert(
        collection_name=PRECEDENTS_COLLECTION_NAME,
        points=points,
    )
    console.print("[green]✓ Ingestion into temporary collection complete.[/]")

    # 7. Create Snapshot for download
    console.print("[blue]Creating Qdrant collection snapshot for export...[/]")
    snapshot_info = client.create_snapshot(collection_name=PRECEDENTS_COLLECTION_NAME)
    snapshot_name = snapshot_info.name
    
    # Calculate snapshot path in Colab
    colab_snapshot_path = f"{QDRANT_PATH}/collections/{PRECEDENTS_COLLECTION_NAME}/snapshots/{snapshot_name}"
    local_export_path = f"./{PRECEDENTS_COLLECTION_NAME}.snapshot"
    
    # Copy snapshot file to Colab root for easy access
    if os.path.exists(colab_snapshot_path):
        import shutil
        shutil.copy2(colab_snapshot_path, local_export_path)
        console.print(f"\n[bold green]✓ Snapshot successfully created at: {local_export_path}[/]")
        
        if IN_COLAB:
            console.print("[bold cyan]Download this file to your local machine using the Colab Files sidebar,[/]")
            console.print("[bold cyan]or run the following in the next cell:[/]")
            console.print("  from google.colab import files")
            console.print(f"  files.download('{local_export_path}')")
    else:
        console.print(f"[red]Could not locate snapshot file at {colab_snapshot_path}[/]")

    # 8. Print Ingestion Table Summary
    table = Table(title="Colab Precedents Ingestion Summary", show_header=True, header_style="bold magenta")
    table.add_column("Precedents Processed", justify="right")
    table.add_column("Export Snapshot File", justify="left")
    table.add_row(str(len(cases)), local_export_path)
    console.print("\n")
    console.print(Panel(table, border_style="green", title="[bold green]GPU Run Complete[/]"))


if __name__ == "__main__":
    main()
