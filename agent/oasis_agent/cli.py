"""
Command Line Interface for oasis-agent using Typer and Rich.
Commands:
  - run: Execute autonomous review and remediation for an issue
  - review: Review an existing PR against its target issue
  - configure: Interactive setup of free-tier API tokens and GitHub credentials
  - status: Check connectivity and rate limits for all providers and GitHub
  - history: View past runs and gatekeeper verdicts
"""

import os
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt

from oasis_agent import __version__
from oasis_agent.config import load_config, save_config, OasisConfig
from oasis_agent.models import GitDiffSummary, IssueContext
from oasis_agent.llm.client import LLMClient
from oasis_agent.llm.router import LLMRouter
from oasis_agent.evaluator.judge import MeaningfulnessJudge
from oasis_agent.github_api.client import GitHubClientManager
from oasis_agent.github_api.pull_requests import PullRequestManager
from oasis_agent.repo_context.cloner import RepoCloner
from oasis_agent.reporter.store import HistoryStore
from oasis_agent.reporter.formatter import sanitize_for_console
from oasis_agent.orchestrator import OasisAgentOrchestrator, PRIVACY_BANNER

import sys
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

app = typer.Typer(
    name="oasis-agent",
    help="Autonomous CLI Agent that reviews and manages GitHub PRs for meaningfulness before pushing.",
    add_completion=False,
)
console = Console(legacy_windows=False)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", "-v", help="Show oasis-agent version and exit"),
):
    if version:
        console.print(f"[bold cyan]oasis-agent[/] version [green]{__version__}[/]")
        raise typer.Exit()
    if ctx.invoked_subcommand is None:
        console.print(Panel(
            f"[bold cyan]oasis-agent[/] [dim]v{__version__}[/]\n"
            "Autonomous Gatekeeper for GitHub Pull Requests powered by free-tier LLM providers.\n\n"
            "Run [bold]oasis-agent --help[/] to see available commands.",
            title="oasis-agent",
            border_style="cyan"
        ))


@app.command()
def configure():
    """Interactively configure free-tier LLM API keys and GitHub credentials into .env."""
    console.print(Panel(
        "Configure API keys for free-tier LLM providers and GitHub.\n"
        "Keys will be saved securely to local [bold].env[/bold] file and excluded via [bold].gitignore[/bold].",
        title="oasis-agent Setup",
        border_style="cyan"
    ))

    env_path = Path(".env")
    current_env = {}
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                current_env[k.strip()] = v.strip()

    def ask_key(env_var: str, desc: str, url: str) -> str:
        current_val = current_env.get(env_var) or os.environ.get(env_var, "")
        prompt_text = f"[bold]{desc}[/] ({env_var})\n[dim]{url}[/]"
        if current_val:
            masked = current_val[:4] + "..." + current_val[-4:] if len(current_val) > 8 else "****"
            val = Prompt.ask(prompt_text, default=masked, console=console)
            return current_val if val == masked else val
        else:
            return Prompt.ask(prompt_text, default="", console=console)

    openrouter_key = ask_key("OPENROUTER_API_KEY", "OpenRouter Key (Free: DeepSeek-R1, Qwen-Coder)", "https://openrouter.ai/keys")
    groq_key = ask_key("GROQ_API_KEY", "Groq Key (Free: Llama 3.3 70B)", "https://console.groq.com/keys")
    google_key = ask_key("GOOGLE_API_KEY", "Google AI Studio Key (Free: Gemini Flash)", "https://aistudio.google.com/app/apikey")
    nvidia_key = ask_key("NVIDIA_API_KEY", "NVIDIA NIM Key (Free credits: Llama 3.1 70B)", "https://build.nvidia.com/")
    gh_token = ask_key("GITHUB_TOKEN", "GitHub Personal Access Token (repo scope)", "https://github.com/settings/tokens")

    env_lines = [
        f"OPENROUTER_API_KEY={openrouter_key}",
        f"GROQ_API_KEY={groq_key}",
        f"GOOGLE_API_KEY={google_key}",
        f"NVIDIA_API_KEY={nvidia_key}",
        f"GITHUB_TOKEN={gh_token}",
    ]
    env_path.write_text("\n".join(env_lines) + "\n", encoding="utf-8")

    # Ensure .env is in .gitignore
    gitignore_path = Path(".gitignore")
    if gitignore_path.exists():
        gi_content = gitignore_path.read_text(encoding="utf-8")
        if ".env" not in gi_content:
            gitignore_path.write_text(gi_content + "\n.env\n", encoding="utf-8")
    else:
        gitignore_path.write_text(".env\n", encoding="utf-8")

    # Update privacy consent
    config = load_config()
    config.privacy.warning_dismissed = True
    save_config(config)

    console.print("[bold green]✓ Successfully configured credentials in .env and verified .gitignore![/]")


@app.command()
def status(
    config_path: Optional[str] = typer.Option(None, "--config", "-c", help="Path to custom config file"),
):
    """Check connectivity, model reachability, and rate limits for all providers."""
    cfg = load_config(config_path)
    router = LLMRouter(cfg)

    console.print(Panel("Checking Provider Connectivity & GitHub Authentication...", title="oasis-agent Status", border_style="cyan"))

    # 1. LLM Providers Table
    table = Table(title="Free-Tier LLM Providers Status", show_header=True)
    table.add_column("Provider Name", style="bold cyan")
    table.add_column("Model", style="white")
    table.add_column("Configured Key", style="dim")
    table.add_column("Ping Status", style="bold")
    table.add_column("Latency", justify="right")

    for name in cfg.providers.keys():
        p_cfg = cfg.providers[name]
        info = router.check_provider_health(name)
        configured_str = "[green]Found[/]" if info["configured"] else f"[yellow]Missing ({p_cfg.api_key_env})[/]"
        
        if info["reachable"]:
            status_str = "[green]Operational[/]"
            latency_str = f"{info['latency_ms']}ms"
        else:
            status_str = f"[red]{info['status']}[/]"
            latency_str = "-"

        table.add_row(name, p_cfg.model, configured_str, status_str, latency_str)

    console.print(table)

    # 2. GitHub Auth & Rate Limit Table
    gh_mgr = GitHubClientManager()
    rl_info = gh_mgr.get_rate_limit_info()
    gh_table = Table(title="GitHub API Authentication", show_header=True)
    gh_table.add_column("Property", style="bold")
    gh_table.add_column("Value")

    gh_table.add_row("Authenticated", "[green]Yes[/]" if rl_info["authenticated"] else "[yellow]No (Unauthenticated / Limited)[/]")
    if rl_info["authenticated"]:
        gh_table.add_row("Hourly Limit", str(rl_info["limit"]))
        gh_table.add_row("Remaining Calls", str(rl_info["remaining"]))
        gh_table.add_row("Reset Time", rl_info["reset_time"])
    else:
        gh_table.add_row("Details", rl_info["status"])

    console.print(gh_table)


@app.command()
def work(
    repo: str = typer.Option(..., "--repo", "-r", help="GitHub repo URL or 'owner/repo' to clone"),
    issue: int = typer.Option(..., "--issue", "-i", help="GitHub Issue number to link and resolve"),
    directory: Optional[str] = typer.Option(None, "--dir", "-d", help="Local directory to clone into (defaults to ./<repo-name>)"),
    config_path: Optional[str] = typer.Option(None, "--config", "-c", help="Path to custom config YAML"),
):
    """Clone a repository locally, set up the git branch, and link the issue for developer editing."""
    cfg = load_config(config_path)
    orchestrator = OasisAgentOrchestrator(config=cfg, console=console)
    res = orchestrator.prepare_workspace(
        repo_url_or_path=repo,
        issue_number=issue,
        target_dir=directory,
    )
    dest_path = res["dest_path"]
    branch = res["branch"]
    issue_ctx = res["issue"]
    stack = res["stack"]

    console.print()
    console.print(Panel(
        f"[bold green]✓ Repository Ready for Development![/]\n\n"
        f"• [bold]Working Directory:[/] {dest_path}\n"
        f"• [bold]Active Branch:[/] [yellow]{branch}[/]\n"
        f"• [bold]Target Issue:[/] #{issue_ctx.issue_number} - {issue_ctx.title}\n"
        f"• [bold]Detected Stack:[/] {', '.join(stack['languages'])} (Test: {stack['test_command']})\n\n"
        f"[bold cyan]Next Steps:[/]\n"
        f"  1. Open [bold]{dest_path}[/] in your code editor.\n"
        f"  2. Make your code changes and write tests.\n"
        f"  3. From inside [bold]{dest_path}[/], run:\n"
        f"     • [bold]oasis-agent check[/] : Test meaningfulness without pushing.\n"
        f"     • [bold]oasis-agent push[/]  : Evaluate meaningfulness, push, and open PR!",
        title="oasis-agent Work Setup",
        border_style="green",
    ))


@app.command()
def push(
    directory: Optional[str] = typer.Option(None, "--dir", "-d", help="Path to local repository workspace (defaults to current dir)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Evaluate meaningfulness without pushing to GitHub or opening PR"),
    clean: bool = typer.Option(True, "--clean/--keep", help="Automatically delete local repository workspace once PR is created (defaults to True)"),
    post_rejection_comment: Optional[bool] = typer.Option(None, "--post-rejection-comment", help="Post comment to GitHub issue if rejected"),
    config_path: Optional[str] = typer.Option(None, "--config", "-c", help="Path to custom config YAML"),
):
    """Evaluate developer's code changes for meaningfulness and push/open PR if approved."""
    cfg = load_config(config_path)
    orchestrator = OasisAgentOrchestrator(config=cfg, console=console)
    report, exit_code = orchestrator.evaluate_and_push(
        repo_dir=directory,
        dry_run=dry_run,
        post_rejection_comment=post_rejection_comment,
        clean=clean,
    )
    raise typer.Exit(code=exit_code)


@app.command()
def check(
    directory: Optional[str] = typer.Option(None, "--dir", "-d", help="Path to local repository workspace (defaults to current dir)"),
    config_path: Optional[str] = typer.Option(None, "--config", "-c", help="Path to custom config YAML"),
):
    """Pre-flight check: evaluate developer's current code changes without pushing (dry-run)."""
    cfg = load_config(config_path)
    orchestrator = OasisAgentOrchestrator(config=cfg, console=console)
    report, exit_code = orchestrator.evaluate_and_push(
        repo_dir=directory,
        dry_run=True,
    )
    raise typer.Exit(code=exit_code)


@app.command()
def run(
    repo: str = typer.Option(..., "--repo", "-r", help="GitHub repo URL (or 'owner/repo' or local path)"),
    issue: int = typer.Option(..., "--issue", "-i", help="GitHub Issue number to resolve"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Evaluate meaningfulness without pushing or opening PR"),
    clean: bool = typer.Option(True, "--clean/--keep", help="Automatically delete local repository workspace once PR is created (defaults to True)"),
    post_rejection_comment: Optional[bool] = typer.Option(None, "--post-rejection-comment", help="Post comment to GitHub issue if rejected"),
    config_path: Optional[str] = typer.Option(None, "--config", "-c", help="Path to custom config YAML"),
):
    """Autonomously inspect issue, propose code edits, evaluate meaningfulness, and manage PR."""
    cfg = load_config(config_path)
    orchestrator = OasisAgentOrchestrator(config=cfg, console=console)
    report, exit_code = orchestrator.run(
        repo_url_or_path=repo,
        issue_number=issue,
        dry_run=dry_run,
        post_rejection_comment=post_rejection_comment,
        clean=clean,
    )
    raise typer.Exit(code=exit_code)


@app.command()
def review(
    pr: int = typer.Argument(..., help="Pull Request number to review"),
    repo: str = typer.Option(..., "--repo", "-r", help="GitHub repo URL or 'owner/repo'"),
    config_path: Optional[str] = typer.Option(None, "--config", "-c", help="Path to custom config YAML"),
):
    """Review an existing PR against its linked issue for meaningfulness."""
    cfg = load_config(config_path)
    console.print(f"[bold cyan]Fetching and reviewing PR #{pr} on {repo}...[/]")
    gh_mgr = GitHubClientManager()
    pr_mgr = PullRequestManager(gh_mgr)
    owner, repo_name = RepoCloner.parse_repo_identifier(repo)
    full_repo = f"{owner}/{repo_name}"

    try:
        pr_obj = pr_mgr.get_pull_request(full_repo, pr)
    except Exception as e:
        console.print(f"[red]Failed to fetch PR #{pr}: {e}[/]")
        raise typer.Exit(code=1)

    # Extract diff and title
    diff_summary = GitDiffSummary(
        files_changed=[f.filename for f in pr_obj.get_files()],
        insertions=pr_obj.additions,
        deletions=pr_obj.deletions,
        diff_content=pr_obj.get_files()[0].patch if pr_obj.get_files() else "",
    )
    issue_ctx = IssueContext(
        repo_url=repo,
        repo_name=full_repo,
        issue_number=pr,
        title=pr_obj.title,
        body=pr_obj.body or "",
    )

    llm_client = LLMClient(config=cfg)
    judge = MeaningfulnessJudge(llm_client, gatekeeper_config=cfg.gatekeeper)
    verdict = judge.evaluate(issue=issue_ctx, diff_summary=diff_summary)

    # Output review
    clean_reasoning = sanitize_for_console(verdict.reasoning)
    console.print(Panel(
        f"[bold]PR #{pr}: {pr_obj.title}[/]\n"
        f"Verdict: [bold {'green' if verdict.meaningful else 'red'}]{'MEANINGFUL' if verdict.meaningful else 'REJECTED'}[/]\n"
        f"Confidence: {verdict.confidence:.2f}\n\n"
        f"Reasoning:\n{clean_reasoning}",
        title="oasis-agent PR Review",
        border_style="green" if verdict.meaningful else "red"
    ))


@app.command()
def history(
    limit: int = typer.Option(10, "--limit", "-n", help="Number of recent runs to display"),
    config_path: Optional[str] = typer.Option(None, "--config", "-c", help="Path to custom config YAML"),
):
    """List historical agent runs from local SQLite database."""
    cfg = load_config(config_path)
    store = HistoryStore(cfg.reporting.database_path)
    runs = store.get_recent_runs(limit=limit)

    if not runs:
        console.print("[dim]No historical runs found in database.[/]")
        return

    table = Table(title=f"oasis-agent Recent Runs (Last {len(runs)})", show_header=True)
    table.add_column("Run ID", style="bold cyan")
    table.add_column("Timestamp", style="dim")
    table.add_column("Repository")
    table.add_column("Issue", justify="right")
    table.add_column("Status")
    table.add_column("Verdict")
    table.add_column("Confidence", justify="right")
    table.add_column("PR URL", style="blue")

    for r in runs:
        status_color = (
            "green" if "opened" in r["status"]
            else ("cyan" if "dry_run" in r["status"]
            else ("magenta" if "llm_unavailable" in r["status"] else "red"))
        )
        verdict_color = "green" if r["meaningful"] == 1 else "red"
        verdict_text = "Meaningful" if r["meaningful"] == 1 else "Rejected"

        table.add_row(
            r["run_id"],
            r["timestamp"][:19].replace("T", " "),
            r["repo_url"][:25],
            f"#{r['issue_number']}",
            f"[{status_color}]{r['status']}[/]",
            f"[{verdict_color}]{verdict_text}[/]",
            f"{r['confidence']:.2f}",
            r["pr_url"] or "-",
        )

    console.print(table)


if __name__ == "__main__":
    app()
