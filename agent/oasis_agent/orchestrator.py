"""
End-to-end Orchestrator for oasis-agent:
Coordinates context building, code editing, test execution, gatekeeper evaluation,
PR creation or rejection handling, and reporting.
"""

import datetime
import logging
import os
import shutil
import stat
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel

from oasis_agent.config import OasisConfig, load_config
from oasis_agent.models import (
    CodeEditsProposal,
    GitDiffSummary,
    IssueContext,
    MeaningfulnessVerdict,
    ReviewReport,
    RunMetrics,
    RunStatus,
    TestRunResult,
)
from oasis_agent.llm.client import LLMClient, LLMUnavailableError
from oasis_agent.llm.prompts import CODE_EDIT_PROMPT, PR_DESCRIPTION_PROMPT
from oasis_agent.repo_context.cloner import RepoCloner
from oasis_agent.repo_context.inspector import RepoInspector
from oasis_agent.repo_context.search import CodebaseSearcher
from oasis_agent.repo_context.editor import CodebaseEditor
from oasis_agent.evaluator.judge import MeaningfulnessJudge
from oasis_agent.evaluator.test_runner import LocalTestRunner
from oasis_agent.git_ops.client import GitClient, GitError
from oasis_agent.git_ops.branch_manager import BranchManager
from oasis_agent.github_api.client import GitHubClientManager
from oasis_agent.github_api.issues import IssueManager
from oasis_agent.github_api.pull_requests import PullRequestManager
from oasis_agent.github_api.checks import ChecksMonitor
from oasis_agent.reporter.formatter import ReportFormatter
from oasis_agent.reporter.store import HistoryStore
from oasis_agent.reporter.comments import generate_pr_comment, generate_issue_rejection_comment

logger = logging.getLogger("oasis_agent.orchestrator")


PRIVACY_BANNER = """
[bold yellow]⚠️  DATA PRIVACY NOTICE[/bold yellow]
oasis-agent is configured to use [bold]free-tier LLM providers[/bold] (OpenRouter, Groq, Google AI Studio, NVIDIA NIM).
These third-party providers may log or process prompts according to their terms of service.
[bold]oasis-agent should ONLY be run against public repositories or codebases you are authorized to share.[/bold]
"""


class OasisAgentOrchestrator:
    """Coordinates the autonomous PR review and remediation lifecycle."""

    def __init__(self, config: Optional[OasisConfig] = None, console: Optional[Console] = None):
        self.config = config or load_config()
        self.console = console or Console()
        self.metrics = RunMetrics()
        self.llm_client = LLMClient(config=self.config, metrics=self.metrics)
        self.formatter = ReportFormatter(self.console)
        self.history_store = HistoryStore(self.config.reporting.database_path)

    @staticmethod
    def cleanup_workspace(work_dir: Path, console: Optional[Console] = None) -> bool:
        """
        Safely and thoroughly clean up and delete the local workspace directory
        after code has been approved and pushed to GitHub.
        Handles Windows read-only git files and active process directory locks.
        """
        work_dir = Path(work_dir).resolve()
        home = Path.home().resolve()
        pkg_root = Path(__file__).resolve().parent.parent.resolve()
        monorepo_root = pkg_root.parent.resolve()

        # Safety: Never delete root, user home, agent package directory, or repository root
        if work_dir in [home, pkg_root, monorepo_root] or work_dir in home.parents:
            if console:
                console.print(f"[yellow]Safety check: Refusing to delete protected directory {work_dir}[/]")
            return False

        # On Windows, change Python's working directory out of work_dir to prevent WinError 32
        try:
            os.chdir(work_dir.parent)
        except Exception:
            try:
                os.chdir(home)
            except Exception:
                pass

        def _remove_readonly(func, path, _):
            try:
                os.chmod(path, stat.S_IWRITE)
                func(path)
            except Exception:
                pass

        # In Python 3.12+, 'onerror' is deprecated in favor of 'onexc'
        rmtree_kwargs = (
            {"onexc": _remove_readonly}
            if sys.version_info >= (3, 12)
            else {"onerror": _remove_readonly}
        )

        # Attempt full directory deletion
        try:
            shutil.rmtree(work_dir, **rmtree_kwargs)
        except Exception:
            pass

        if not work_dir.exists():
            if console:
                console.print(f"[bold green]✓ Successfully cleaned up and removed workspace:[/] [dim]{work_dir}[/]")
            return True

        # If parent shell process holds a lock on the root folder, clear internal items
        for item in list(work_dir.iterdir()):
            try:
                if item.is_dir():
                    try:
                        shutil.rmtree(item, **rmtree_kwargs)
                    except Exception:
                        pass
                else:
                    os.chmod(item, stat.S_IWRITE)
                    item.unlink(missing_ok=True)
            except Exception:
                pass

        remaining = list(work_dir.iterdir())
        if not remaining:
            if console:
                console.print(
                    f"[bold green]✓ Cleared all repository files in:[/] [cyan]{work_dir}[/]\n"
                    f"[dim](Directory will finish disappearing when your terminal navigates away: 'cd ..')[/]"
                )
            return True
        else:
            if console:
                console.print(f"[yellow]Partial cleanup completed. Remaining items: {[r.name for r in remaining]}[/]")
            return False

    def print_privacy_notice(self):
        """Display data privacy warning if not previously acknowledged."""
        if not self.config.privacy.warning_dismissed:
            self.console.print(PRIVACY_BANNER)

    def run(
        self,
        repo_url_or_path: str,
        issue_number: int,
        dry_run: bool = False,
        post_rejection_comment: Optional[bool] = None,
        custom_diff: Optional[str] = None,
        clean: Optional[bool] = None,
    ) -> tuple[ReviewReport, int]:
        """
        Execute full lifecycle for a repository and issue.
        Returns: (report, exit_code)
          Exit code 0: PR created or dry-run successful
          Exit code 1: PR rejected by gatekeeper
          Exit code 2: LLM unavailable
          Exit code 3: General error
        """
        run_id = str(uuid.uuid4())[:8]
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        self.print_privacy_notice()

        # Step 1: Initialize GitHub API & Issue Context
        gh_mgr = GitHubClientManager()
        issue_mgr = IssueManager(gh_mgr)
        pr_mgr = PullRequestManager(gh_mgr)

        owner, repo_name = RepoCloner.parse_repo_identifier(repo_url_or_path)
        full_repo_name = f"{owner}/{repo_name}"

        self.console.print(f"[bold cyan]oasis-agent initiating run {run_id}[/] for {full_repo_name} (Issue #{issue_number})")

        issue_ctx: Optional[IssueContext] = None
        # Try fetching real issue from GitHub if possible
        if gh_mgr.token and owner != "local":
            try:
                self.console.print(f"Fetching Issue #{issue_number} from GitHub...")
                issue_ctx = issue_mgr.get_issue(full_repo_name, issue_number)
            except Exception as e:
                logger.warning(f"Could not fetch issue from GitHub API: {e}. Falling back to local issue stub.")

        if not issue_ctx:
            issue_ctx = IssueContext(
                repo_url=repo_url_or_path,
                repo_name=full_repo_name,
                issue_number=issue_number,
                title=f"Issue #{issue_number}",
                body="Automated issue context for oasis-agent evaluation.",
            )

        # Step 2: Clone or Retrieve Cached Repository
        self.console.print("Accessing repository...")
        cloner = RepoCloner(
            cache_dir=self.config.git.cache_dir,
            shallow=self.config.git.shallow_clone,
        )
        try:
            repo_dir = cloner.clone_or_get_cached(repo_url_or_path)
        except Exception as e:
            self.console.print(f"[red]Failed to clone or access repository: {e}[/]")
            return self._build_error_report(run_id, timestamp, issue_ctx, f"Cloning error: {e}", dry_run), 3

        # Check for local issue description file if running locally
        if owner == "local" or not issue_ctx.body or issue_ctx.body.startswith("Automated issue"):
            for candidate_name in [f"ISSUE_{issue_number}.md", f"issue_{issue_number}.md", "ISSUE.md"]:
                cand_path = repo_dir / candidate_name
                if cand_path.exists():
                    text = cand_path.read_text(encoding="utf-8").strip()
                    lines = text.splitlines()
                    issue_title = lines[0].lstrip("# ").strip() if lines else f"Issue #{issue_number}"
                    issue_body = "\n".join(lines[1:]).strip() if len(lines) > 1 else text
                    issue_ctx.title = issue_title
                    issue_ctx.body = issue_body
                    self.console.print(f"[dim]Loaded local issue details from {candidate_name}[/]")
                    break

        # Step 3: Context Building & Stack Detection
        self.console.print("Building codebase context map...")
        inspector = RepoInspector(repo_dir)
        stack_info = inspector.detect_stack()
        tech_stack_desc = ", ".join(stack_info["languages"])
        self.console.print(f"Detected stack: [green]{tech_stack_desc}[/] (Test Runner: {stack_info['test_command']})")

        editor = CodebaseEditor(repo_dir)
        git_client = GitClient(repo_dir)
        branch_mgr = BranchManager(git_client, prefix=self.config.git.branch_prefix)

        # Step 4: Propose & Apply Edits
        diff_summary: Optional[GitDiffSummary] = None

        if custom_diff:
            # Used for tests and dry-run worked examples
            diff_summary = GitDiffSummary(
                files_changed=["modified_file"],
                insertions=len([l for l in custom_diff.splitlines() if l.startswith("+")]),
                deletions=len([l for l in custom_diff.splitlines() if l.startswith("-")]),
                diff_content=custom_diff,
            )
        else:
            searcher = CodebaseSearcher(repo_dir)
            keywords = searcher.extract_keywords(issue_ctx)
            relevant_files = searcher.rank_relevant_files(keywords, top_k=3)

            files_context_parts = []
            for file_path, _ in relevant_files:
                try:
                    content = editor.read_file(file_path)
                    files_context_parts.append(f"### File: {file_path}\n```\n{content[:2000]}\n```")
                except Exception:
                    continue
            files_context = "\n\n".join(files_context_parts) or "No specific files matched."

            self.console.print("Generating code remediation patch with LLM...")
            try:
                edit_prompt = CODE_EDIT_PROMPT.format(
                    issue_number=issue_ctx.issue_number,
                    issue_title=issue_ctx.title,
                    issue_body=issue_ctx.body,
                    files_content=files_context,
                )
                proposal, edit_provider = self.llm_client.complete(
                    prompt=edit_prompt,
                    task_type="code_editing",
                    response_model=CodeEditsProposal,
                )
                logger.info(f"Edit proposal generated by {edit_provider}")

                if isinstance(proposal, CodeEditsProposal):
                    for edit in proposal.edits:
                        rel_path = edit.file_path.replace("\\", "/").lstrip("/")
                        full_p = repo_dir / rel_path
                        if full_p.exists():
                            editor.edit_file(rel_path, edit.new_content)
                            logger.info(f"Applied edit to {rel_path}")
                        else:
                            editor.create_file(rel_path, edit.new_content)
                            logger.info(f"Created file {rel_path}")

                diff_summary = editor.compute_diff_summary()
            except LLMUnavailableError as err:
                self.console.print(f"[magenta]All LLM providers unavailable during code edit: {err}[/]")
                return self._build_llm_unavailable_report(run_id, timestamp, issue_ctx, err, dry_run), 2
            except Exception as e:
                logger.warning(f"Error during code edit generation: {e}")
                diff_summary = editor.compute_diff_summary()

        if not diff_summary:
            diff_summary = editor.compute_diff_summary()

        # Step 5: Execute Local Test Suite
        test_results: Optional[TestRunResult] = None
        if self.config.gatekeeper.run_local_tests:
            self.console.print("Running local test suite...")
            runner = LocalTestRunner(repo_dir)
            test_results = runner.run_tests(timeout_seconds=60)

        # Step 6: Meaningfulness Evaluation
        self.console.print("Running Gatekeeper Meaningfulness Check...")
        judge = MeaningfulnessJudge(self.llm_client, gatekeeper_config=self.config.gatekeeper)

        try:
            verdict = judge.evaluate(
                issue=issue_ctx,
                diff_summary=diff_summary,
                test_results=test_results,
                tech_stack=tech_stack_desc,
            )
        except LLMUnavailableError as err:
            self.console.print(f"[magenta]All LLM providers unavailable during meaningfulness judgment: {err}[/]")
            editor.rollback_all()
            return self._build_llm_unavailable_report(run_id, timestamp, issue_ctx, err, dry_run, diff_summary, test_results), 2

        # Step 7: Gatekeeper Decision Branch
        pr_url: Optional[str] = None
        pr_number: Optional[int] = None
        branch_name: Optional[str] = None
        ci_status: Optional[str] = None
        exit_code = 0

        if verdict.meaningful and verdict.recommended_action == "APPROVE_AND_PR":
            if dry_run:
                self.console.print("[green]Gatekeeper approved change. Dry-run mode enabled: skipping git push and PR creation.[/]")
                status = RunStatus.COMPLETED_DRY_RUN
                exit_code = 0
                editor.rollback_all()
            else:
                self.console.print("[bold green]Gatekeeper APPROVED change! Creating branch and opening Pull Request...[/]")
                branch_name = branch_mgr.prepare_issue_branch(issue_number)
                git_client.stage_all()
                commit_msg = f"{self.config.git.commit_message_prefix}(#{issue_number}): resolve {issue_ctx.title}"
                git_client.commit(commit_msg)

                try:
                    self.console.print(f"Pushing branch '{branch_name}' to remote...")
                    git_client.push(branch_name, token=gh_mgr.token)

                    # Generate PR description
                    pr_desc_prompt = PR_DESCRIPTION_PROMPT.format(
                        issue_number=issue_number,
                        issue_title=issue_ctx.title,
                        issue_body=issue_ctx.body,
                        diff_summary=f"+{diff_summary.insertions} / -{diff_summary.deletions}",
                        test_results="Passed" if (test_results and test_results.passed) else "Not executed",
                    )
                    pr_body, _ = self.llm_client.complete(
                        prompt=pr_desc_prompt,
                        task_type="pr_description_generation",
                    )

                    pr_title = f"Fixes #{issue_number}: {issue_ctx.title}"
                    pr_number, pr_url = pr_mgr.create_pull_request(
                        repo_full_name=full_repo_name,
                        title=pr_title,
                        body=pr_body,
                        head_branch=branch_name,
                    )
                    self.console.print(f"[bold green]Pull Request successfully opened:[/] {pr_url}")

                    # Post review comment to PR
                    report_preview = ReviewReport(
                        run_id=run_id,
                        timestamp=timestamp,
                        repo_url=issue_ctx.repo_url,
                        issue_number=issue_number,
                        issue_title=issue_ctx.title,
                        status=RunStatus.COMPLETED_PR_OPENED,
                        meaningfulness=verdict,
                        diff_summary=diff_summary,
                        test_results=test_results,
                        pr_url=pr_url,
                        pr_number=pr_number,
                        branch_name=branch_name,
                        metrics=self.metrics,
                        dry_run=False,
                    )
                    pr_comment = generate_pr_comment(report_preview)
                    pr_mgr.post_pr_comment(full_repo_name, pr_number, pr_comment)

                    # Monitor CI check runs if triggered
                    checks_monitor = ChecksMonitor(gh_mgr)
                    commit_sha = git_client._run(["rev-parse", "HEAD"])
                    ci_status = checks_monitor.poll_for_completion(
                        full_repo_name, commit_sha, timeout_seconds=45, poll_interval=10
                    )

                    status = RunStatus.COMPLETED_PR_OPENED
                    exit_code = 0
                except Exception as e:
                    logger.error(f"Error during push/PR creation: {e}")
                    self.console.print(f"[red]Failed to push or create PR: {e}[/]")
                    status = RunStatus.ERROR
                    exit_code = 3
        else:
            # Change REJECTED or FLAGGED
            status = (
                RunStatus.FLAGGED_HUMAN_REVIEW
                if verdict.recommended_action == "FLAG_FOR_HUMAN_REVIEW"
                else RunStatus.COMPLETED_REJECTED
            )
            exit_code = 1
            self.console.print(f"[bold red]Change REJECTED by Gatekeeper:[/] {verdict.rejection_reason or verdict.reasoning}")
            self.console.print("[dim]Aborting git operations: no branch pushed and no PR opened.[/]")
            editor.rollback_all()
            branch_mgr.cleanup_on_rejection()

            # Optional: Post rejection comment on issue
            should_comment = (
                post_rejection_comment
                if post_rejection_comment is not None
                else self.config.reporting.comment_on_rejection
            )
            if should_comment and gh_mgr.token and owner != "local":
                try:
                    rejection_comment = generate_issue_rejection_comment(
                        ReviewReport(
                            run_id=run_id,
                            timestamp=timestamp,
                            repo_url=issue_ctx.repo_url,
                            issue_number=issue_number,
                            issue_title=issue_ctx.title,
                            status=status,
                            meaningfulness=verdict,
                            diff_summary=diff_summary,
                            test_results=test_results,
                            metrics=self.metrics,
                            dry_run=dry_run,
                        )
                    )
                    issue_mgr.post_comment(full_repo_name, issue_number, rejection_comment)
                    self.console.print(f"[dim]Posted explanation comment on Issue #{issue_number}[/]")
                except Exception as e:
                    logger.debug(f"Failed to post rejection comment to issue: {e}")

        # Step 8: Build, Export, and Render Final Review Report
        report = ReviewReport(
            run_id=run_id,
            timestamp=timestamp,
            repo_url=issue_ctx.repo_url,
            issue_number=issue_number,
            issue_title=issue_ctx.title,
            status=status,
            meaningfulness=verdict,
            diff_summary=diff_summary,
            test_results=test_results,
            pr_url=pr_url,
            pr_number=pr_number,
            branch_name=branch_name,
            metrics=self.metrics,
            ci_status=ci_status,
            dry_run=dry_run,
        )

        json_path, md_path = self.formatter.export_artifacts(report, self.config.reporting.output_dir)
        self.history_store.save_run(report, json_path, md_path)
        self.formatter.render_cli(report)
        self.console.print(f"[dim]Artifacts saved: {json_path} and {md_path}[/]")

        should_clean = self.config.reporting.clean_workspace_on_success if clean is None else clean
        if status == RunStatus.COMPLETED_PR_OPENED and should_clean and not dry_run:
            self.console.print("[dim]Cleaning up local repository workspace...[/]")
            self.cleanup_workspace(repo_dir, self.console)

        return report, exit_code

    def _build_llm_unavailable_report(
        self,
        run_id: str,
        timestamp: str,
        issue: IssueContext,
        err: LLMUnavailableError,
        dry_run: bool,
        diff: Optional[GitDiffSummary] = None,
        test_res: Optional[TestRunResult] = None,
    ) -> ReviewReport:
        verdict = MeaningfulnessVerdict(
            meaningful=False,
            confidence=0.0,
            reasoning=f"LLM providers unavailable: {err}",
            recommended_action="REJECT",
            rejection_reason=f"LLM providers unavailable: {err}",
        )
        report = ReviewReport(
            run_id=run_id,
            timestamp=timestamp,
            repo_url=issue.repo_url,
            issue_number=issue.issue_number,
            issue_title=issue.title,
            status=RunStatus.LLM_UNAVAILABLE,
            meaningfulness=verdict,
            diff_summary=diff or GitDiffSummary(),
            test_results=test_res,
            metrics=self.metrics,
            dry_run=dry_run,
        )
        json_p, md_p = self.formatter.export_artifacts(report, self.config.reporting.output_dir)
        self.history_store.save_run(report, json_p, md_p)
        self.formatter.render_cli(report)
        return report

    def _build_error_report(
        self,
        run_id: str,
        timestamp: str,
        issue: IssueContext,
        error_msg: str,
        dry_run: bool,
    ) -> ReviewReport:
        verdict = MeaningfulnessVerdict(
            meaningful=False,
            confidence=0.0,
            reasoning=f"Execution failed with error: {error_msg}",
            recommended_action="REJECT",
            rejection_reason=error_msg,
        )
        report = ReviewReport(
            run_id=run_id,
            timestamp=timestamp,
            repo_url=issue.repo_url,
            issue_number=issue.issue_number,
            issue_title=issue.title,
            status=RunStatus.ERROR,
            meaningfulness=verdict,
            diff_summary=GitDiffSummary(),
            metrics=self.metrics,
            dry_run=dry_run,
        )
        json_p, md_p = self.formatter.export_artifacts(report, self.config.reporting.output_dir)
        self.history_store.save_run(report, json_p, md_p)
        self.formatter.render_cli(report)
        return report

    def prepare_workspace(
        self,
        repo_url_or_path: str,
        issue_number: int,
        target_dir: Optional[str] = None,
    ) -> dict:
        """
        Stage 1 of Developer-Led Workflow:
        Clones the repo locally to a working folder, checks out the issue branch,
        fetches the issue from GitHub, and saves metadata into .oasis-agent/issue.json.
        """
        self.print_privacy_notice()
        gh_mgr = GitHubClientManager()
        issue_mgr = IssueManager(gh_mgr)

        owner, repo_name = RepoCloner.parse_repo_identifier(repo_url_or_path)
        full_repo_name = f"{owner}/{repo_name}"

        dest_path = Path(target_dir).resolve() if target_dir else Path.cwd() / repo_name
        self.console.print(f"[bold cyan]Preparing local workspace for {full_repo_name} (Issue #{issue_number})...[/]")

        # 1. Clone repo if not already cloned
        if not (dest_path / ".git").exists():
            dest_path.mkdir(parents=True, exist_ok=True)
            cloner = RepoCloner(shallow=False)
            clone_url = cloner.get_authenticated_url(repo_url_or_path)
            self.console.print(f"Cloning repository into [green]{dest_path}[/]...")
            res = subprocess.run(
                ["git", "clone", clone_url, str(dest_path)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            if res.returncode != 0:
                raise RuntimeError(f"Git clone failed: {res.stderr.strip()}")
        else:
            self.console.print(f"Using existing repository at [green]{dest_path}[/]")

        # 2. Fetch issue from GitHub or fallback
        issue_ctx = None
        if gh_mgr.token and owner != "local":
            try:
                self.console.print(f"Fetching Issue #{issue_number} details from GitHub...")
                issue_ctx = issue_mgr.get_issue(full_repo_name, issue_number)
            except Exception as e:
                logger.warning(f"Could not fetch issue from GitHub: {e}")

        if not issue_ctx:
            # Check local file or fallback
            for cand in [f"ISSUE_{issue_number}.md", f"issue_{issue_number}.md", "ISSUE.md"]:
                cand_p = dest_path / cand
                if cand_p.exists():
                    t = cand_p.read_text(encoding="utf-8").strip()
                    lines = t.splitlines()
                    issue_ctx = IssueContext(
                        repo_url=repo_url_or_path,
                        repo_name=full_repo_name,
                        issue_number=issue_number,
                        title=lines[0].lstrip("# ").strip() if lines else f"Issue #{issue_number}",
                        body="\n".join(lines[1:]).strip() if len(lines) > 1 else t,
                    )
                    break

        if not issue_ctx:
            issue_ctx = IssueContext(
                repo_url=repo_url_or_path,
                repo_name=full_repo_name,
                issue_number=issue_number,
                title=f"Issue #{issue_number}",
                body="Issue context linked by oasis-agent.",
            )

        # Save to .oasis-agent/issue.json
        meta_dir = dest_path / ".oasis-agent"
        meta_dir.mkdir(parents=True, exist_ok=True)
        (meta_dir / "issue.json").write_text(issue_ctx.model_dump_json(indent=2), encoding="utf-8")

        # 3. Create and switch to isolated branch
        git_client = GitClient(dest_path)
        branch_mgr = BranchManager(git_client, prefix=self.config.git.branch_prefix)
        branch_name = branch_mgr.prepare_issue_branch(issue_number)

        # Publish the new branch to remote origin if authenticated
        if gh_mgr.token and owner != "local":
            try:
                self.console.print(f"Publishing new branch '[yellow]{branch_name}[/]' to remote origin...")
                git_client.push(branch_name, token=gh_mgr.token)
                self.console.print(f"[bold green]✓ Successfully published branch '{branch_name}' to remote origin.[/]")
            except Exception as e:
                logger.warning(f"Initial branch push to remote origin: {e}")
                self.console.print(f"[dim]Initial remote push note: {e}. Changes will be pushed when running 'oasis-agent push'.[/]")

        # 4. Detect stack & test runner
        inspector = RepoInspector(dest_path)
        stack = inspector.detect_stack()

        return {
            "dest_path": dest_path,
            "branch": branch_name,
            "issue": issue_ctx,
            "stack": stack,
        }

    def evaluate_and_push(
        self,
        repo_dir: Optional[str] = None,
        dry_run: bool = False,
        post_rejection_comment: Optional[bool] = None,
        clean: Optional[bool] = None,
    ) -> tuple[ReviewReport, int]:
        """
        Stage 3 of Developer-Led Workflow:
        Inspects the developer's modifications, runs local tests, evaluates meaningfulness,
        and pushes the branch & opens a PR if approved (or aborts the push if rejected).
        """
        run_id = str(uuid.uuid4())[:8]
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        self.print_privacy_notice()

        work_dir = Path(repo_dir).resolve() if repo_dir else Path.cwd().resolve()
        if not (work_dir / ".git").exists():
            self.console.print(f"[red]Error: '{work_dir}' is not a git repository.[/]")
            raise RuntimeError(f"Directory {work_dir} is not a git repository.")

        git_client = GitClient(work_dir)
        current_branch = git_client.get_current_branch()

        # Step 1: Load Issue Context from .oasis-agent/issue.json
        issue_file = work_dir / ".oasis-agent" / "issue.json"
        issue_ctx = None
        if issue_file.exists():
            try:
                issue_ctx = IssueContext.model_validate_json(issue_file.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning(f"Could not parse {issue_file}: {e}")

        if not issue_ctx:
            # Try to infer issue number from branch name (e.g. oasis-agent/fix-issue-42)
            issue_num = 1
            if "fix-issue-" in current_branch:
                try:
                    issue_num = int(current_branch.split("fix-issue-")[-1])
                except ValueError:
                    pass
            # Try finding local issue file
            issue_title = f"Issue #{issue_num}"
            issue_body = ""
            for cand in [f"ISSUE_{issue_num}.md", f"issue_{issue_num}.md", "ISSUE.md"]:
                cand_p = work_dir / cand
                if cand_p.exists():
                    t = cand_p.read_text(encoding="utf-8").strip()
                    lines = t.splitlines()
                    issue_title = lines[0].lstrip("# ").strip() if lines else issue_title
                    issue_body = "\n".join(lines[1:]).strip() if len(lines) > 1 else t
                    break

            owner, repo_name = RepoCloner.parse_repo_identifier(str(work_dir))
            issue_ctx = IssueContext(
                repo_url=f"https://github.com/{owner}/{repo_name}",
                repo_name=f"{owner}/{repo_name}",
                issue_number=issue_num,
                title=issue_title,
                body=issue_body or "Target issue for oasis-agent review.",
            )

        self.console.print(Panel(
            f"[bold cyan]oasis-agent Gatekeeper Check (Run {run_id})[/]\n"
            f"Repository: [green]{work_dir}[/]\n"
            f"Branch: [yellow]{current_branch}[/]\n"
            f"Target Issue: #{issue_ctx.issue_number} - {issue_ctx.title}",
            title="Pre-Push Meaningfulness Review",
            border_style="cyan",
        ))

        # Step 2: Extract Developer's Diff
        self.console.print("Inspecting your code modifications...")
        # Check against base branch if on a feature branch
        base_branch = "main"
        for candidate_base in ["main", "master"]:
            try:
                git_client._run(["rev-parse", "--verify", candidate_base])
                base_branch = candidate_base
                break
            except Exception:
                continue

        diff_summary = git_client.get_diff(base=base_branch)
        # If branch diff against base is empty, check uncommitted changes
        if not diff_summary.diff_content.strip():
            diff_summary = git_client.get_diff()

        if not diff_summary.diff_content.strip():
            self.console.print("[bold red]Gatekeeper Aborted: No changes detected in your workspace or branch![/]")
            return self._build_error_report(
                run_id, timestamp, issue_ctx, "Diff is completely empty. Please make code changes before submitting.", dry_run
            ), 1

        self.console.print(
            f"Detected changes across [cyan]{len(diff_summary.files_changed)} file(s)[/]: "
            f"[green]+{diff_summary.insertions}[/], [red]-{diff_summary.deletions}[/]"
        )

        # Step 3: Run Local Test Suite
        inspector = RepoInspector(work_dir)
        stack_info = inspector.detect_stack()
        tech_stack_desc = ", ".join(stack_info["languages"])
        test_results = None

        if self.config.gatekeeper.run_local_tests:
            self.console.print("Running local test suite...")
            runner = LocalTestRunner(work_dir)
            test_results = runner.run_tests(timeout_seconds=60)

        # Step 4: Gatekeeper Meaningfulness Evaluation
        self.console.print("Evaluating code meaningfulness against target issue...")
        judge = MeaningfulnessJudge(self.llm_client, gatekeeper_config=self.config.gatekeeper)

        try:
            verdict = judge.evaluate(
                issue=issue_ctx,
                diff_summary=diff_summary,
                test_results=test_results,
                tech_stack=tech_stack_desc,
            )
        except LLMUnavailableError as err:
            self.console.print(f"[magenta]All LLM providers unavailable during meaningfulness judgment: {err}[/]")
            return self._build_llm_unavailable_report(run_id, timestamp, issue_ctx, err, dry_run, diff_summary, test_results), 2

        # Step 5: Decision
        pr_url = None
        pr_number = None
        ci_status = None
        gh_mgr = GitHubClientManager()
        pr_mgr = PullRequestManager(gh_mgr)
        owner, repo_name = RepoCloner.parse_repo_identifier(issue_ctx.repo_url)
        full_repo_name = f"{owner}/{repo_name}"

        if verdict.meaningful and verdict.recommended_action == "APPROVE_AND_PR":
            if dry_run:
                self.console.print(
                    "[bold green]✓ Gatekeeper APPROVED your changes![/]\n"
                    "[dim]Dry-run mode enabled: skipping git push and PR creation.[/]"
                )
                status = RunStatus.COMPLETED_DRY_RUN
                exit_code = 0
            else:
                self.console.print("[bold green]✓ Gatekeeper APPROVED your changes! Pushing branch and opening Pull Request...[/]")
                try:
                    # Stage and commit any uncommitted changes
                    git_client.stage_all()
                    commit_msg = f"{self.config.git.commit_message_prefix}(#{issue_ctx.issue_number}): resolve {issue_ctx.title}"
                    try:
                        git_client.commit(commit_msg)
                    except Exception:
                        pass  # Already committed

                    # Push branch
                    self.console.print(f"Pushing branch '{current_branch}' to remote origin...")
                    try:
                        git_client.push(current_branch, token=gh_mgr.token)
                    except GitError as ge:
                        if any(phrase in str(ge).lower() for phrase in ["non-fast-forward", "fetch first", "rejected"]):
                            logger.info("Non-fast-forward detected on feature branch; force pushing updated commits...")
                            git_client.push(current_branch, token=gh_mgr.token, force=True)
                        else:
                            raise

                    # Generate PR description
                    pr_desc_prompt = PR_DESCRIPTION_PROMPT.format(
                        issue_number=issue_ctx.issue_number,
                        issue_title=issue_ctx.title,
                        issue_body=issue_ctx.body,
                        diff_summary=f"+{diff_summary.insertions} / -{diff_summary.deletions}",
                        test_results="Passed" if (test_results and test_results.passed) else "Not executed",
                    )
                    pr_body, _ = self.llm_client.complete(
                        prompt=pr_desc_prompt,
                        task_type="pr_description_generation",
                    )

                    pr_title = f"Fixes #{issue_ctx.issue_number}: {issue_ctx.title}"
                    pr_number, pr_url = pr_mgr.create_pull_request(
                        repo_full_name=full_repo_name,
                        title=pr_title,
                        body=pr_body,
                        head_branch=current_branch,
                    )
                    self.console.print(f"[bold green]Pull Request successfully opened:[/] [link={pr_url}]{pr_url}[/link]")

                    # Post review comment
                    report_preview = ReviewReport(
                        run_id=run_id,
                        timestamp=timestamp,
                        repo_url=issue_ctx.repo_url,
                        issue_number=issue_ctx.issue_number,
                        issue_title=issue_ctx.title,
                        status=RunStatus.COMPLETED_PR_OPENED,
                        meaningfulness=verdict,
                        diff_summary=diff_summary,
                        test_results=test_results,
                        pr_url=pr_url,
                        pr_number=pr_number,
                        branch_name=current_branch,
                        metrics=self.metrics,
                        dry_run=False,
                    )
                    pr_comment = generate_pr_comment(report_preview)
                    pr_mgr.post_pr_comment(full_repo_name, pr_number, pr_comment)

                    # Monitor CI checks
                    checks_monitor = ChecksMonitor(gh_mgr)
                    commit_sha = git_client._run(["rev-parse", "HEAD"])
                    ci_status = checks_monitor.poll_for_completion(
                        full_repo_name, commit_sha, timeout_seconds=30, poll_interval=10
                    )

                    status = RunStatus.COMPLETED_PR_OPENED
                    exit_code = 0
                except Exception as e:
                    logger.error(f"Error during push/PR creation: {e}")
                    self.console.print(f"[red]Failed to push or create PR: {e}[/]")
                    if "403" in str(e) or "Permission to" in str(e) or "denied" in str(e):
                        self.console.print(
                            "\n[bold yellow]💡 GitHub Permission (403) Troubleshooting:[/]\n"
                            "1. If using a [bold]Fine-Grained Personal Access Token (github_pat_...)[/]:\n"
                            "   • Visit: [cyan]https://github.com/settings/tokens[/cyan]\n"
                            "   • Edit the token and ensure under [bold]Repository permissions[/bold]:\n"
                            "     - [bold green]Contents[/bold green]: set to [bold]Read and write[/bold] (required for pushing commits)\n"
                            "     - [bold green]Pull requests[/bold green]: set to [bold]Read and write[/bold] (required for opening PRs)\n"
                            "     - [bold green]Issues[/bold green]: set to [bold]Read and write[/bold]\n"
                            "   • Under [bold]Repository access[/bold], verify that this repository is selected.\n"
                            "2. If using a [bold]Classic Token (ghp_...)[/]:\n"
                            "   • Ensure the [bold green]repo[/bold green] scope checkbox is enabled.\n"
                        )
                    status = RunStatus.ERROR
                    exit_code = 3
        else:
            # Change REJECTED or FLAGGED
            status = (
                RunStatus.FLAGGED_HUMAN_REVIEW
                if verdict.recommended_action == "FLAG_FOR_HUMAN_REVIEW"
                else RunStatus.COMPLETED_REJECTED
            )
            exit_code = 1
            self.console.print(f"[bold red]❌ PUSH BLOCKED by Gatekeeper:[/] {verdict.rejection_reason or verdict.reasoning}")
            self.console.print("[dim]Aborting git operations: no branch was pushed and no PR was opened.[/]")
            self.console.print("[yellow]Your local files were left untouched so you can refine your code.[/]")

        # Build and render report
        report = ReviewReport(
            run_id=run_id,
            timestamp=timestamp,
            repo_url=issue_ctx.repo_url,
            issue_number=issue_ctx.issue_number,
            issue_title=issue_ctx.title,
            status=status,
            meaningfulness=verdict,
            diff_summary=diff_summary,
            test_results=test_results,
            pr_url=pr_url,
            pr_number=pr_number,
            branch_name=current_branch,
            metrics=self.metrics,
            ci_status=ci_status,
            dry_run=dry_run,
        )

        json_path, md_path = self.formatter.export_artifacts(report, self.config.reporting.output_dir)
        self.history_store.save_run(report, json_path, md_path)
        self.formatter.render_cli(report)
        self.console.print(f"[dim]Artifacts saved: {json_path} and {md_path}[/]")

        should_clean = self.config.reporting.clean_workspace_on_success if clean is None else clean
        if status == RunStatus.COMPLETED_PR_OPENED and should_clean and not dry_run:
            self.console.print("[dim]Cleaning up local repository workspace...[/]")
            self.cleanup_workspace(work_dir, self.console)

        return report, exit_code
