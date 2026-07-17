"""Nyaya AI — Statutory Corpus Ingestion Script (Hybrid).

Modes:
    python ingest.py                # Full ingestion from HuggingFace datasets
    python ingest.py --backfill     # One-time: tag all existing points as 'original'
    python ingest.py --amend FILE   # Admin: amend specific sections from a local file

Full ingestion:
    1. Connect to Qdrant (local file-based)
    2. Create nyaya_corpus collection (dense + sparse named vectors)
    3. Load mratanusarkar/Indian-Laws (primary, pre-sectioned)
    4. Load geekyrakshit/indian-legal-acts (secondary, raw text, dedup-filtered)
    5. Embed all chunks with BGE-M3 (dense + sparse in one pass)
    6. Upsert to Qdrant
    7. Print summary

Amendment ingestion (--amend):
    Interactive workflow for corpus admin to update specific sections
    with amendment text sourced from India Code or similar authoritative sources.
    Finds existing points by act_name + section_number, marks them as
    amended/omitted, and optionally upserts new amended text.

Backfill (--backfill):
    One-time payload-only update: sets amendment_status='original' on all
    existing points that don't have it yet. No re-embedding required.
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import date
from pathlib import Path

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
from nyaya_ai.ingest.loaders import load_geekyrakshit, load_mratanusarkar, load_gsms_b
from nyaya_ai.retrieval.embedder import Embedder
from nyaya_ai.schemas import CorpusChunk
from nyaya_ai.store.qdrant import (
    create_collection,
    find_points_by_section,
    get_point_count,
    set_payload_bulk,
    update_point_payload,
    upsert_chunks,
)

console = Console()

EMBED_BATCH_SIZE = 32
UPSERT_BATCH_SIZE = 100


# ===================================================================
# Mode: Full ingestion (default)
# ===================================================================

def run_full_ingestion(reforms_only: bool = False) -> None:
    """Run the full ingestion pipeline with hybrid encoding."""
    start_time = time.time()

    console.print(
        Panel(
            "[bold white]Nyaya AI — Statutory Corpus Ingestion (Hybrid)[/]\n"
            "Ingesting Indian legal Acts with dense + sparse vectors.",
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

    if reforms_only:
        console.print("[yellow]Skipping primary and secondary corpuses. Ingesting BNS, BNSS, and BSA (2023 Reforms) only.[/]")
        all_chunks = load_gsms_b(registry)
    else:
        # Primary dataset — pre-sectioned, registers in dedup
        primary_chunks = load_mratanusarkar(registry)

        # Secondary dataset — raw text, chunked, dedup-filtered
        secondary_chunks = load_geekyrakshit(registry)
        
        # 2023 Reforms dataset — new criminal reform codes (BNS, BNSS, BSA)
        reforms_chunks = load_gsms_b(registry)

        # Combine
        all_chunks = primary_chunks + secondary_chunks + reforms_chunks

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
    # Step 3: Embed all chunks (dense + sparse in one pass)
    # ------------------------------------------------------------------
    console.print("\n[bold]Step 3:[/] Embedding chunks with BGE-M3 (dense + sparse)...\n")
    embedder = Embedder()

    all_dense: list[list[float]] = []
    all_sparse: list[dict[int, float]] = []
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
            "Embedding (hybrid)...", total=len(texts)
        )

        for i in range(0, len(texts), EMBED_BATCH_SIZE):
            batch = texts[i : i + EMBED_BATCH_SIZE]
            hybrid = embedder.embed_documents_hybrid(batch, batch_size=EMBED_BATCH_SIZE)
            all_dense.extend(hybrid.dense)
            all_sparse.extend(hybrid.sparse)
            progress.update(task, advance=len(batch))

    console.print(
        f"[green]  Embedded {len(all_dense)} chunks "
        f"(dense: {EMBEDDING_DIM}d + sparse: lexical weights).[/]"
    )

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
            batch_dense = all_dense[i : i + UPSERT_BATCH_SIZE]
            batch_sparse = all_sparse[i : i + UPSERT_BATCH_SIZE]
            upsert_chunks(
                batch_chunks,
                batch_dense,
                sparse_vectors=batch_sparse,
            )
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
    table.add_row("Embedding dimension (dense)", str(EMBEDDING_DIM))
    table.add_row("Vectors per point", "dense (1024d) + sparse (lexical)")
    table.add_row("Collection", COLLECTION_NAME)
    table.add_row("Time taken", f"{elapsed:.1f}s")

    console.print()
    console.print(table)
    console.print(
        f"\n[bold green]✓[/] Ingestion complete. "
        f"Run [bold]python query.py[/] to start chatting.\n"
    )


# ===================================================================
# Mode: --backfill (one-time amendment_status migration)
# ===================================================================

def run_backfill() -> None:
    """One-time backfill: set amendment_status='original' on all existing points."""
    console.print(
        Panel(
            "[bold white]Nyaya AI — Backfill Amendment Status[/]\n"
            "Setting amendment_status='original' on all existing points.\n"
            "This is a payload-only update — no re-embedding required.",
            border_style="blue",
        )
    )

    try:
        count = get_point_count()
    except ConnectionError as e:
        console.print(f"\n[red bold]ERROR:[/] {e}")
        sys.exit(1)

    if count == 0:
        console.print("[yellow]Collection is empty. Nothing to backfill.[/]")
        return

    console.print(f"\n  Points in collection: [cyan]{count:,}[/]")
    console.print("  Setting amendment_status='original' on all points...\n")

    set_payload_bulk({"amendment_status": "original"})

    console.print(
        f"\n[bold green]✓[/] Backfill complete. "
        f"{count:,} points now have amendment_status='original'.\n"
    )


# ===================================================================
# Mode: --amend (interactive amendment workflow)
# ===================================================================

def run_amend(file_path: str) -> None:
    """Interactive admin workflow: amend specific sections from a local file."""
    from nyaya_ai.contracts.extractor import extract_contract_text

    path = Path(file_path)

    console.print(
        Panel(
            "[bold white]Nyaya AI — Amendment Ingestion[/]\n"
            f"Source file: [cyan]{path.name}[/]",
            border_style="blue",
        )
    )

    # ------------------------------------------------------------------
    # Step 1: Extract text from the source file
    # ------------------------------------------------------------------
    console.print("\n[bold]Step 1:[/] Extracting text from source file...")

    if not path.exists():
        console.print(f"\n[red bold]ERROR:[/] File not found: {path}")
        sys.exit(1)

    extracted = extract_contract_text(path)

    if extracted.status == "failure":
        console.print(f"\n[red bold]ERROR:[/] {extracted.error_message}")
        sys.exit(1)

    # Combine all text
    if extracted.pages:
        full_text = "\n\n".join(p.text for p in extracted.pages)
    elif extracted.paragraphs:
        full_text = "\n\n".join(extracted.paragraphs)
    else:
        console.print("\n[red bold]ERROR:[/] No text extracted from file.")
        sys.exit(1)

    # Show preview
    preview = full_text[:500]
    console.print(
        Panel(
            f"{preview}{'...' if len(full_text) > 500 else ''}",
            title="[bold]Extracted Text Preview[/]",
            border_style="dim",
        )
    )
    console.print(f"  Total characters: [cyan]{len(full_text):,}[/]\n")

    # ------------------------------------------------------------------
    # Step 2: Gather amendment metadata (once for all sections)
    # ------------------------------------------------------------------
    console.print("[bold]Step 2:[/] Amendment metadata\n")

    act_name = console.input(
        "  [bold cyan]Which Act does this amendment apply to?[/]\n"
        "  (e.g. 'Information Technology Act 2000')\n"
        "  > "
    ).strip()
    if not act_name:
        console.print("[red]Act name is required. Aborting.[/]")
        sys.exit(1)

    amended_by = console.input(
        "\n  [bold cyan]Name of the amending Act:[/]\n"
        "  (e.g. 'IT (Amendment) Act, 2008')\n"
        "  > "
    ).strip()
    if not amended_by:
        console.print("[red]Amending Act name is required. Aborting.[/]")
        sys.exit(1)

    year_str = console.input(
        "\n  [bold cyan]Amendment year:[/]\n"
        "  > "
    ).strip()
    try:
        amendment_year = int(year_str)
    except ValueError:
        console.print(f"[red]Invalid year: '{year_str}'. Aborting.[/]")
        sys.exit(1)

    verified_source = console.input(
        "\n  [bold cyan]Verification source[/] (default: 'indiacode.nic.in'):\n"
        "  > "
    ).strip() or "indiacode.nic.in"

    verified_date = date.today().isoformat()
    console.print(f"  Verification date: [cyan]{verified_date}[/]")

    sections_str = console.input(
        "\n  [bold cyan]Section number(s) being amended[/] (comma-separated):\n"
        "  (e.g. '43A, 66A, 72A')\n"
        "  > "
    ).strip()
    if not sections_str:
        console.print("[red]At least one section number is required. Aborting.[/]")
        sys.exit(1)

    sections = [s.strip() for s in sections_str.split(",") if s.strip()]

    console.print(
        f"\n  [bold green]Amendment scope:[/] {act_name} — "
        f"sections {', '.join(sections)} — by {amended_by} ({amendment_year})"
    )

    # ------------------------------------------------------------------
    # Step 3: Process each section
    # ------------------------------------------------------------------
    console.print(f"\n[bold]Step 3:[/] Processing {len(sections)} section(s)...\n")

    # Load embedder only if we'll need to upsert new text
    embedder = None

    summary_updated: list[str] = []
    summary_inserted: list[str] = []
    summary_not_found: list[str] = []

    for section_num in sections:
        console.print(f"  [bold]--- Section {section_num} ---[/]")

        # Find existing point(s) in nyaya_corpus
        existing = find_points_by_section(act_name, section_num)

        if not existing:
            console.print(
                f"    [yellow]⚠ No existing points found for "
                f"'{act_name}' §{section_num}.[/]"
            )
            summary_not_found.append(section_num)

            # Ask if they want to insert it as a new section anyway
            insert_anyway = console.input(
                "    Insert as a new section anyway? [y/N] > "
            ).strip().lower()
            if insert_anyway != "y":
                console.print("    Skipping.\n")
                continue
        else:
            console.print(
                f"    Found [cyan]{len(existing)}[/] existing point(s):"
            )
            for i, pt in enumerate(existing, 1):
                text_preview = pt.get("text", "")[:120]
                status = pt.get("amendment_status", "unknown")
                console.print(
                    f"      [{i}] ID: {pt['id'][:8]}... | "
                    f"status: {status} | {text_preview}..."
                )

        # Ask status for this section
        console.print()
        status_input = console.input(
            f"    [bold cyan]Status for §{section_num}?[/] "
            f"[amended/omitted] > "
        ).strip().lower()

        if status_input not in ("amended", "omitted"):
            console.print(
                f"    [yellow]Invalid status '{status_input}'. "
                f"Must be 'amended' or 'omitted'. Skipping.[/]\n"
            )
            continue

        # Build the payload update for existing points
        amendment_payload = {
            "amendment_status": status_input,
            "amended_by": amended_by,
            "amendment_year": amendment_year,
            "last_verified_source": verified_source,
            "last_verified_date": verified_date,
        }

        # Update existing points
        if existing:
            point_ids = [pt["id"] for pt in existing]
            update_point_payload(point_ids, amendment_payload)
            console.print(
                f"    [green]✓ Updated {len(point_ids)} existing point(s) "
                f"→ amendment_status='{status_input}'[/]"
            )
            summary_updated.append(section_num)

        # If amended: also upsert the NEW text as a new point
        if status_input == "amended":
            console.print(
                f"\n    The extracted text will be indexed as the new "
                f"§{section_num} content."
            )

            # Use the full extracted text for now (single section amendments)
            # For multi-section files, the user should separate them
            new_text = full_text.strip()
            if len(sections) > 1:
                # If amending multiple sections from one file, ask for
                # section-specific text
                console.print(
                    f"\n    [dim]Multiple sections detected. Paste the specific "
                    f"text for §{section_num} below.[/]"
                )
                console.print(
                    "    [dim](Enter a blank line when done)[/]"
                )
                lines = []
                while True:
                    line = console.input("    | ")
                    if line == "":
                        break
                    lines.append(line)
                if lines:
                    new_text = "\n".join(lines)
                else:
                    console.print(
                        "    [yellow]No text entered. Using full "
                        "extracted text.[/]"
                    )

            # Create the new CorpusChunk
            new_chunk = CorpusChunk(
                act_name=act_name,
                section_number=section_num,
                text=new_text,
                source=f"admin:{verified_source}",
                amendment_status="amended",
                amended_by=amended_by,
                amendment_year=amendment_year,
                last_verified_source=verified_source,
                last_verified_date=verified_date,
            )

            # Embed and upsert
            if embedder is None:
                console.print(
                    "\n    [dim]Loading embedder for new text...[/]"
                )
                embedder = Embedder()

            hybrid = embedder.embed_documents_hybrid([new_text])
            upsert_chunks(
                [new_chunk],
                hybrid.dense,
                sparse_vectors=hybrid.sparse,
            )
            console.print(
                f"    [green]✓ Inserted new amended point for "
                f"'{act_name}' §{section_num}[/]"
            )
            summary_inserted.append(section_num)

        elif status_input == "omitted":
            console.print(
                f"    [yellow]Section §{section_num} marked as omitted. "
                f"No new text inserted.[/]"
            )
            if not existing:
                # Insert a stub point for omitted sections so retrieval
                # can surface "this section was omitted"
                stub_chunk = CorpusChunk(
                    act_name=act_name,
                    section_number=section_num,
                    text=(
                        f"Section {section_num} of {act_name} has been "
                        f"omitted by {amended_by} ({amendment_year}). "
                        f"This section is no longer in force."
                    ),
                    source=f"admin:{verified_source}",
                    amendment_status="omitted",
                    amended_by=amended_by,
                    amendment_year=amendment_year,
                    last_verified_source=verified_source,
                    last_verified_date=verified_date,
                )

                if embedder is None:
                    console.print(
                        "\n    [dim]Loading embedder for stub text...[/]"
                    )
                    embedder = Embedder()

                hybrid = embedder.embed_documents_hybrid([stub_chunk.text])
                upsert_chunks(
                    [stub_chunk],
                    hybrid.dense,
                    sparse_vectors=hybrid.sparse,
                )
                console.print(
                    f"    [green]✓ Inserted omission stub for "
                    f"'{act_name}' §{section_num}[/]"
                )
                summary_inserted.append(f"{section_num} (stub)")

        console.print()

    # ------------------------------------------------------------------
    # Step 4: Summary
    # ------------------------------------------------------------------
    console.print()
    table = Table(title="Amendment Summary", border_style="green")
    table.add_column("Action", style="cyan")
    table.add_column("Sections", style="white")

    table.add_row("Act amended", act_name)
    table.add_row("Amending Act", f"{amended_by} ({amendment_year})")
    table.add_row("Existing points updated", ", ".join(summary_updated) or "—")
    table.add_row("New points inserted", ", ".join(summary_inserted) or "—")
    table.add_row(
        "Sections not found in corpus",
        ", ".join(summary_not_found) or "—",
    )
    table.add_row("Total points in Qdrant", str(get_point_count()))

    console.print(table)
    console.print(
        f"\n[bold green]✓[/] Amendment ingestion complete.\n"
        f"  📁 Save to: docs/ai-conversations/ as needed\n"
        f"  💾 Commit: \"corpus: amend {act_name} — {amended_by}\"\n"
    )


# ===================================================================
# CLI argument parsing
# ===================================================================

def main() -> None:
    """Parse CLI arguments and dispatch to the appropriate mode."""
    parser = argparse.ArgumentParser(
        description="Nyaya AI — Statutory Corpus Ingestion",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modes:
  (default)             Full ingestion from HuggingFace datasets
  --backfill            One-time: tag all existing points as 'original'
  --amend FILE          Admin: amend specific sections from a local file

Examples:
  python ingest.py
  python ingest.py --backfill
  python ingest.py --amend amendments/it_act_2008.pdf
  python ingest.py --amend amendments/section_66A_omission.txt
        """,
    )
    parser.add_argument(
        "--amend",
        metavar="FILE",
        type=str,
        help="Path to amendment source file (PDF, DOCX, or TXT)",
    )
    parser.add_argument(
        "--backfill",
        action="store_true",
        help="One-time: set amendment_status='original' on all existing points",
    )
    parser.add_argument(
        "--reforms-only",
        action="store_true",
        help="Only ingest the 2023 Criminal Reform Acts (BNS, BNSS, BSA) from GSMS-B",
    )

    args = parser.parse_args()

    if args.backfill and args.amend:
        console.print(
            "[red bold]ERROR:[/] Cannot use --backfill and --amend together."
        )
        sys.exit(1)

    if args.backfill:
        run_backfill()
    elif args.amend:
        run_amend(args.amend)
    else:
        run_full_ingestion(reforms_only=args.reforms_only)


if __name__ == "__main__":
    main()
