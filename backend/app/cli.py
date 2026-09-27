"""Command Line Interface (CLI) for AST-Based Static Analysis & Technical Debt Evaluation.

Renders deterministic metrics, admin KPI cards, and the 6-field violation table.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from app.engine.analyzer import ASTDebtAnalyzer, RepositoryAnalysisResult


def render_analysis_report(repo_result: RepositoryAnalysisResult, console: Console) -> None:
    """Renders formatted Rich console output."""
    console.print()
    console.rule("[bold cyan]AST-Based Static Code Analysis & Technical Debt Evaluation Engine[/bold cyan]")
    console.print(f"[dim]Commit / Repo ID:[/dim] [bold yellow]{repo_result.commit_repo_id}[/bold yellow] | [dim]Target:[/dim] [bold]{repo_result.name}[/bold]")
    console.print()

    # --- 1. ADMIN KPI CARDS ---
    mi_color = "green" if repo_result.overall_maintainability_index >= 80 else ("yellow" if repo_result.overall_maintainability_index >= 65 else "red")
    risk_color = "red" if repo_result.high_risk_file_ratio > 20 else ("yellow" if repo_result.high_risk_file_ratio > 0 else "green")
    backlog_color = "red" if repo_result.total_debt_backlog_hours > 15 else ("yellow" if repo_result.total_debt_backlog_hours > 5 else "green")

    kpi_table = Table.grid(expand=True, padding=(0, 2))
    kpi_table.add_column(ratio=1)
    kpi_table.add_column(ratio=1)
    kpi_table.add_column(ratio=1)

    card_mi = Panel(
        f"[{mi_color}][bold text-2xl]{repo_result.overall_maintainability_index:.1f} / 100[/bold text-2xl][/{mi_color}]\n"
        f"[dim]Formula: 171 - 5.2*ln(V) - 0.23*v(G) - 16.2*ln(SLOC)[/dim]",
        title="[bold]Overall Maintainability Index[/bold]",
        border_style=mi_color,
    )
    card_risk = Panel(
        f"[{risk_color}][bold text-2xl]{repo_result.high_risk_file_ratio:.1f}%[/bold text-2xl][/{risk_color}]\n"
        f"[dim]Files with Cyclomatic Complexity v(G) > 10[/dim]",
        title="[bold]High-Risk File Ratio[/bold]",
        border_style=risk_color,
    )
    card_debt = Panel(
        f"[{backlog_color}][bold text-2xl]{repo_result.total_debt_backlog_hours:.1f} hrs[/bold text-2xl][/{backlog_color}]\n"
        f"[dim]Sum of unresolved Flagged issues effort[/dim]",
        title="[bold]Total Technical Debt Backlog[/bold]",
        border_style=backlog_color,
    )

    kpi_table.add_row(card_mi, card_risk, card_debt)
    console.print(kpi_table)
    console.print()

    # --- 2. SUMMARY METRICS TABLE ---
    summary_table = Table(title="Repository Inventory & Codebase Metrics", expand=True, show_header=True, header_style="bold magenta")
    summary_table.add_column("Files Analyzed", justify="right")
    summary_table.add_column("Total LOC", justify="right")
    summary_table.add_column("Source LOC (SLOC)", justify="right")
    summary_table.add_column("Avg Cyclomatic v(G)", justify="right")
    summary_table.add_column("Total Violations", justify="right")
    summary_table.add_row(
        str(repo_result.total_files),
        str(repo_result.total_loc),
        str(repo_result.total_sloc),
        f"{repo_result.avg_cyclomatic_complexity:.2f}",
        str(len(repo_result.all_violations)),
    )
    console.print(summary_table)
    console.print()

    # --- 3. THE 6 PRIMARY FIELDS RECORD TABLE ---
    viol_table = Table(
        title="AST Violations & Technical Debt Log (Primary 6-Field Schema)",
        expand=True,
        show_header=True,
        header_style="bold blue",
    )
    viol_table.add_column("1. Commit / Repo ID", style="dim", no_wrap=True)
    viol_table.add_column("2. File Path", style="cyan")
    viol_table.add_column("3. Violation Type", style="bold")
    viol_table.add_column("4. Cyclomatic v(G)", justify="center")
    viol_table.add_column("5. Remediation (hrs)", justify="right")
    viol_table.add_column("6. Refactor Status", justify="center")
    viol_table.add_column("Location & Details", style="dim")

    if not repo_result.all_violations:
        viol_table.add_row("-", "-", "No AST violations detected!", "-", "-", "-", "Clean code")
    else:
        for v in repo_result.all_violations:
            vg_color = "red" if v.cyclomatic_complexity > 10 else ("yellow" if v.cyclomatic_complexity > 5 else "green")
            status_style = "bold red" if v.refactor_status == "Flagged" else ("bold green" if v.refactor_status == "Rule-Patched" else "dim")

            viol_table.add_row(
                v.commit_repo_id,
                v.file_path,
                v.violation_type,
                f"[{vg_color}]{v.cyclomatic_complexity}[/{vg_color}]",
                f"{v.remediation_hours:.2f} hrs",
                f"[{status_style}]{v.refactor_status}[/{status_style}]",
                f"L{v.start_line}-L{v.end_line} ({v.node_type}) - {v.message[:65]}...",
            )

    console.print(viol_table)
    console.print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Deterministic AST Static Code Analysis & Technical Debt Engine")
    parser.add_argument("path", help="Path to Python file or directory repository to analyze")
    parser.add_argument("--repo-id", default=None, help="Custom commit / repository identifier (UUID / string)")
    args = parser.parse_args()

    target_path = Path(args.path)
    if not target_path.exists():
        print(f"Error: Target path '{args.path}' does not exist.", file=sys.stderr)
        sys.exit(1)

    console = Console(width=130)
    analyzer = ASTDebtAnalyzer()

    if target_path.is_file():
        file_res = analyzer.analyze_file(target_path, commit_repo_id=args.repo_id)
        # Package into repository result for uniform display
        repo_result = RepositoryAnalysisResult(
            commit_repo_id=file_res.commit_repo_id,
            name=target_path.name,
            files=[file_res],
            total_files=1,
            total_loc=file_res.line_metrics.total_loc,
            total_sloc=file_res.line_metrics.sloc,
            avg_cyclomatic_complexity=float(file_res.cyclomatic_complexity),
            overall_maintainability_index=file_res.maintainability_index,
            high_risk_file_ratio=100.0 if file_res.is_high_risk else 0.0,
            total_debt_backlog_hours=file_res.total_remediation_hours,
            all_violations=file_res.violations,
        )
    else:
        repo_result = analyzer.analyze_repository(target_path, commit_repo_id=args.repo_id)

    render_analysis_report(repo_result, console)


if __name__ == "__main__":
    main()
