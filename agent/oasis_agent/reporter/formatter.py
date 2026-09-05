"""
Report Formatter: Generates Rich CLI visuals, Markdown artifacts, and JSON reports.
"""

import json
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax
from rich.text import Text

from oasis_agent.models import ReviewReport


def sanitize_for_console(text: str) -> str:
    """Sanitize typography characters that fail on Windows cp1252 console."""
    if not text:
        return ""
    return (
        str(text)
        .replace("\u2011", "-")
        .replace("\u2012", "-")
        .replace("\u2013", "-")
        .replace("\u2014", "--")
        .replace("\u2018", "'")
        .replace("\u2019", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2026", "...")
    )


class ReportFormatter:
    """Renders and saves comprehensive run review reports."""

    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console(legacy_windows=False)

    def render_cli(self, report: ReviewReport):
        """Render beautiful Rich terminal UI for the run results."""
        v = report.meaningfulness

        # Color-coded status header
        if report.status == "completed_pr_opened":
            header_color = "bold green"
            title = "PULL REQUEST APPROVED & CREATED"
        elif report.status == "completed_dry_run":
            header_color = "bold cyan"
            title = "DRY RUN COMPLETE (NO PR OPENED)"
        elif report.status == "flagged_human_review":
            header_color = "bold yellow"
            title = "FLAGGED FOR HUMAN REVIEW (LOW CONFIDENCE)"
        elif report.status == "llm_unavailable":
            header_color = "bold magenta"
            title = "RUN HALTED: ALL LLM PROVIDERS UNAVAILABLE"
        else:
            header_color = "bold red"
            title = "CHANGE REJECTED BY MEANINGFULNESS GATEKEEPER"

        self.console.print()
        self.console.print(Panel(
            f"[{header_color}]{title}[/]\n"
            f"[dim]Run ID:[/] {report.run_id} | [dim]Target:[/] {report.repo_url} (Issue #{report.issue_number})\n"
            f"[dim]Issue Title:[/] {report.issue_title}\n"
            + (f"[dim]PR URL:[/] [link={report.pr_url}]{report.pr_url}[/link]\n" if report.pr_url else "")
            + (f"[dim]Branch:[/] {report.branch_name}\n" if report.branch_name else ""),
            border_style=header_color.split()[-1],
            title="oasis-agent Execution Summary",
        ))

        # Evaluation Dimensions Table
        if v.dimension_scores:
            dim_table = Table(title="Meaningfulness Dimensions Analysis", box=None, show_header=True)
            dim_table.add_column("Dimension", style="bold cyan")
            dim_table.add_column("Score", justify="right")
            dim_table.add_column("Assessment", style="dim")

            for dim_name, score_obj in v.dimension_scores.items():
                score_val = score_obj.score
                color = "green" if score_val >= 0.7 else ("yellow" if score_val >= 0.4 else "red")
                dim_table.add_row(
                    dim_name.capitalize(),
                    f"[{color}]{score_val:.2f}[/]",
                    sanitize_for_console(score_obj.reasoning),
                )
            self.console.print(dim_table)

        # Reasoning Panel
        self.console.print(Panel(
            f"[bold]Confidence Score:[/] {v.confidence:.2f}\n"
            f"[bold]Recommended Action:[/] {v.recommended_action}\n\n"
            f"[bold]Gatekeeper Reasoning:[/]\n{sanitize_for_console(v.reasoning)}",
            title="Gatekeeper Evaluation",
            border_style="blue",
        ))

        # Test results
        if report.test_results and report.test_results.executed:
            t_color = "green" if report.test_results.passed else "red"
            t_status = "PASSED" if report.test_results.passed else "FAILED"
            clean_output = sanitize_for_console(report.test_results.output[:400])
            self.console.print(Panel(
                f"[{t_color}]Framework: {report.test_results.framework} | Status: {t_status} (exit code {report.test_results.exit_code})[/]\n\n"
                f"[dim]{clean_output}[/]",
                title="Local Test Suite Results",
                border_style=t_color,
            ))

        # Diff summary
        diff_info = report.diff_summary
        if diff_info.files_changed:
            self.console.print(
                f"[bold]Files Changed ({len(diff_info.files_changed)}):[/] {', '.join(diff_info.files_changed)} "
                f"([green]+{diff_info.insertions}[/], [red]-{diff_info.deletions}[/])"
            )

        # Provider Metrics
        self.console.print(f"[dim]LLM Metrics: {report.metrics.summary_string()}[/]")
        self.console.print()

    def generate_markdown(self, report: ReviewReport) -> str:
        """Generate a complete standalone Markdown review report."""
        v = report.meaningfulness

        dim_rows = []
        for dim, s in v.dimension_scores.items():
            dim_rows.append(f"| **{dim.capitalize()}** | `{s.score:.2f}` | {s.reasoning} |")
        dim_table = "\n".join(dim_rows) if dim_rows else "| None | - | - |"

        test_details = "None executed"
        if report.test_results and report.test_results.executed:
            test_details = (
                f"**Status:** {'PASSED' if report.test_results.passed else 'FAILED'} (Exit code: {report.test_results.exit_code})\n"
                f"**Framework:** {report.test_results.framework}\n\n"
                f"```\n{report.test_results.output}\n```"
            )

        diff_block = f"```diff\n{report.diff_summary.diff_content}\n```" if report.diff_summary.diff_content else "_No diff generated_"

        return f"""# oasis-agent Review Report: Run {report.run_id}

- **Date / Time:** {report.timestamp}
- **Target Repo:** [{report.repo_url}]({report.repo_url})
- **Issue Reference:** Issue #{report.issue_number} - {report.issue_title}
- **Execution Status:** `{report.status.value}`
- **Pull Request:** {f'[{report.pr_url}]({report.pr_url})' if report.pr_url else 'None opened'}
- **Working Branch:** `{report.branch_name or 'None'}`
- **Dry Run:** `{report.dry_run}`

---

## 1. Meaningfulness Evaluation

- **Verdict:** `{'MEANINGFUL (Approved)' if v.meaningful else 'REJECTED'}`
- **Overall Confidence:** `{v.confidence:.2f}`
- **Recommended Action:** `{v.recommended_action}`
- **Rejection Reason:** {v.rejection_reason or 'N/A'}

### Dimension Breakdown
| Dimension | Score | Reasoning |
| :--- | :--- | :--- |
{dim_table}

### Gatekeeper Reasoning
> {v.reasoning}

### Missing Aspects & Risks
- **Missing Aspects:**
{chr(10).join([f'  - {m}' for m in v.missing_aspects]) if v.missing_aspects else '  - None identified'}
- **Identified Risks:**
{chr(10).join([f'  - {r}' for r in v.risks_or_side_effects]) if v.risks_or_side_effects else '  - None identified'}

---

## 2. Test Suite Outcome
{test_details}

---

## 3. Git Diff
- **Files Modified ({len(report.diff_summary.files_changed)}):** `{', '.join(report.diff_summary.files_changed)}`
- **Stats:** +{report.diff_summary.insertions} / -{report.diff_summary.deletions}

{diff_block}

---

## 4. LLM & Failover Metrics
- **Provider Calls:** {report.metrics.summary_string()}
- **Total Invocations:** {report.metrics.total_calls}
- **Failovers Encountered:** {report.metrics.failover_count}

---
*Generated autonomously by oasis-agent*
"""

    def export_artifacts(self, report: ReviewReport, output_dir: str = ".oasis-agent/reports") -> tuple[Path, Path]:
        """Save report as both JSON and Markdown artifacts."""
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        json_file = out_path / f"run_{report.run_id}.json"
        md_file = out_path / f"run_{report.run_id}.md"

        json_file.write_text(report.model_dump_json(indent=2), encoding="utf-8")
        md_file.write_text(self.generate_markdown(report), encoding="utf-8")

        return json_file, md_file
