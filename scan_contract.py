#!/usr/bin/env python3
"""CLI tool for Mode 1 Contract Risk Scanning in Nyaya AI."""

import argparse
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from nyaya_ai.contracts.scanner import scan_contract
from nyaya_ai.schemas import ContractScanResult

console = Console()
error_console = Console(stderr=True)


def print_cli_report(result: ContractScanResult) -> None:
    """Print a user-friendly contract scan report using rich."""
    console.print("\n")
    console.print(
        Panel.fit(
            f"[bold cyan]Nyaya AI Contract Intelligence Scan Report[/]",
            border_style="cyan",
        )
    )

    # 1. Summary details
    table = Table(show_header=False, box=None)
    table.add_row("[bold]Contract Name:[/]", result.contract_name)
    table.add_row("[bold]Total Clauses Scanned:[/]", str(result.total_clauses_scanned))
    table.add_row("[bold]Scan Confidence:[/]", f"{result.scan_confidence * 100:.1f}%")

    # Status coloring
    status_mapping = {
        "risks_found": "[bold red]⚠️ RISKS FOUND[/]",
        "no_material_risks_found": "[bold green]✅ NO MATERIAL RISKS FOUND[/]",
        "insufficient_evidence": "[bold yellow]❓ INSUFFICIENT EVIDENCE (NO RELEVANT LAW MATCHES)[/]",
        "ocr_required": "[bold blue]📷 OCR REQUIRED (SCANNED PDF)[/]",
    }
    status_str = status_mapping.get(result.status, result.status.upper())
    table.add_row("[bold]Scan Status:[/]", status_str)

    console.print(table)
    console.print("\n" + "-" * 80 + "\n")

    # 2. Detailed message
    console.print(f"[bold]Summary Message:[/]\n{result.message}\n")

    # 3. Findings list
    if result.status == "risks_found":
        console.print(f"[bold red]Identified Risks ({len(result.findings)}):[/]\n")
        for idx, finding in enumerate(result.findings, 1):
            finding_text = (
                f"[bold]Clause Reference:[/] Clause {finding.clause_number} (Page {finding.page})\n"
                f"[bold]Clause Text:[/]\n[italic]\"{finding.clause_text.strip()}\"[/]\n\n"
                f"[bold]Conflicting Statute:[/] {finding.conflicting_act}, Section {finding.conflicting_section}\n"
                f"[bold]Statutory Quote:[/]\n[yellow]\"{finding.conflicting_law_quote.strip()}\"[/]\n\n"
                f"[bold]Legal Explanation:[/]\n{finding.explanation}\n\n"
                f"[bold green]Recommended Action:[/] [green]{finding.recommended_action}[/]"
            )
            
            # Panel border color based on risk level
            border_color = "red" if finding.risk_level == "high" else "yellow"
            
            console.print(
                Panel(
                    finding_text,
                    title=f"[bold]Finding #{idx} — {finding.clause_type.upper()} ({finding.risk_level.upper()} RISK)[/]",
                    border_style=border_color,
                    expand=False,
                )
            )
            console.print("\n")
    elif result.status == "no_material_risks_found":
        console.print(
            "[bold green]No statutory conflicts identified. All analyzed clauses are grounded and conform with retrieved Indian laws.[/]"
        )
    elif result.status == "insufficient_evidence":
        console.print(
            "[bold yellow]Unable to verify legal conformity. None of the contract clauses matched entries in the statutory corpus with sufficient similarity scores. Verify coverage or update relevance settings.[/]"
        )
    elif result.status == "ocr_required":
        console.print(
            "[bold blue]Scanned Document Detected. The PDF contains no extractable machine-readable text. Please process with an OCR scanner tool before evaluating with Nyaya AI.[/]"
        )

    console.print("\n[dim]Disclaimer: Nyaya AI provides automated compliance analysis based on statutory provisions. It does not constitute legal advice.[/]\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scan an Indian contract against the Nyaya AI statutory database for conflicts and void clauses."
    )
    parser.add_argument(
        "contract_path",
        type=str,
        help="Path to the contract file (PDF or DOCX).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON serialization of the ScanResult model.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=None,
        help="Override default relevance pre-filter threshold (0.0 to 1.0).",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print verbose step-by-step diagnostic evaluation logs to the console.",
    )

    args = parser.parse_args()
    contract_path = Path(args.contract_path)

    if not contract_path.exists():
        error_console.print(f"[red]Error: Contract file not found at '{args.contract_path}'[/]")
        sys.exit(1)

    try:
        scan_args = {}
        if args.threshold is not None:
            scan_args["relevance_threshold"] = args.threshold
        if args.verbose:
            scan_args["verbose"] = True

        result = scan_contract(contract_path, **scan_args)

        if args.json:
            print(result.model_dump_json(indent=2))
        else:
            print_cli_report(result)

    except Exception as e:
        error_console.print(f"[bold red]Scan Failed with error:[/] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
