"""
Git CLI client wrapper with robust error handling and execution tracking.
"""

import logging
import os
import re
import subprocess
from pathlib import Path
from typing import List, Optional
from oasis_agent.models import GitDiffSummary

logger = logging.getLogger("oasis_agent.git_client")


class GitError(Exception):
    def __init__(self, message: str, returncode: int = 1, stderr: str = ""):
        super().__init__(message)
        self.returncode = returncode
        self.stderr = stderr


class GitClient:
    """Provides high-level Git operations over a local repository."""

    def __init__(self, repo_dir: Path):
        self.repo_dir = Path(repo_dir).resolve()
        self.ensure_oasis_excluded()

    def ensure_oasis_excluded(self):
        """Ensure .oasis-agent directory is excluded in .git/info/exclude so it is never committed."""
        try:
            exclude_file = self.repo_dir / ".git" / "info" / "exclude"
            if exclude_file.parent.exists():
                content = exclude_file.read_text(encoding="utf-8") if exclude_file.exists() else ""
                if ".oasis-agent" not in content:
                    exclude_file.write_text(content.rstrip() + "\n\n# oasis-agent internal artifacts\n.oasis-agent/\n.oasis-agent\n", encoding="utf-8")
        except Exception as e:
            logger.debug(f"Could not update .git/info/exclude: {e}")

    def _run(self, args: List[str], timeout: int = 40) -> str:
        """Run a git command in the repository directory."""
        logger.debug(f"Running git command: git {' '.join(args)} in {self.repo_dir}")
        res = subprocess.run(
            ["git"] + args,
            cwd=self.repo_dir,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        if res.returncode != 0:
            stderr_text = (res.stderr or "").strip()
            err_msg = f"Git command failed: git {' '.join(args)}\nExit code: {res.returncode}\nStderr: {stderr_text}"
            logger.debug(err_msg)
            raise GitError(err_msg, returncode=res.returncode, stderr=res.stderr)
        return (res.stdout or "").strip()

    def get_current_branch(self) -> str:
        return self._run(["rev-parse", "--abbrev-ref", "HEAD"])

    def create_and_checkout_branch(self, branch_name: str) -> str:
        """Create a new branch and switch to it."""
        try:
            return self._run(["checkout", "-b", branch_name])
        except GitError as e:
            # If branch already exists locally, checkout directly
            if "already exists" in e.stderr:
                return self._run(["checkout", branch_name])
            raise

    def stage_all(self):
        """Stage all modified and newly created files, ensuring .oasis-agent is never tracked."""
        self.ensure_oasis_excluded()
        self._run(["add", "-A"])
        # Unstage .oasis-agent if it was staged or tracked
        try:
            self._run(["rm", "-r", "--cached", "--ignore-unmatch", ".oasis-agent"])
        except Exception:
            pass

    def commit(self, message: str, author_name: str = "oasis-agent", author_email: str = "oasis-agent@users.noreply.github.com") -> str:
        """Commit staged changes with conventional commit message."""
        # Set local config for commit author if needed
        return self._run([
            "-c", f"user.name={author_name}",
            "-c", f"user.email={author_email}",
            "commit", "-m", message,
        ])

    def get_diff(self, base: Optional[str] = None) -> GitDiffSummary:
        """Get diff of uncommitted changes or diff against a base branch, excluding .oasis-agent."""
        path_exclude = [":!.oasis-agent", ":!.oasis-agent/**"]
        if base:
            raw_diff = self._run(["diff", f"{base}...HEAD", "--", "."] + path_exclude)
            stat = self._run(["diff", "--stat", f"{base}...HEAD", "--", "."] + path_exclude)
        else:
            raw_diff = self._run(["diff", "HEAD", "--", "."] + path_exclude)
            stat = self._run(["diff", "--stat", "HEAD", "--", "."] + path_exclude)

        files = []
        insertions = 0
        deletions = 0

        for line in raw_diff.splitlines():
            if line.startswith("+++ b/"):
                fname = line.removeprefix("+++ b/")
                if not fname.startswith(".oasis-agent"):
                    files.append(fname)
            elif line.startswith("+") and not line.startswith("+++"):
                insertions += 1
            elif line.startswith("-") and not line.startswith("---"):
                deletions += 1

        return GitDiffSummary(
            files_changed=list(dict.fromkeys(files)),
            insertions=insertions,
            deletions=deletions,
            diff_content=raw_diff,
        )

    def push(self, branch_name: str, remote: str = "origin", force: bool = False, token: Optional[str] = None) -> str:
        """Push branch to remote with authenticated token if available, bypassing credential helper overrides."""
        token = token or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")

        # Determine clean remote URL and GitHub owner/repo if applicable
        owner_repo = None
        try:
            current_remote = self._run(["remote", "get-url", remote])
            clean_url = re.sub(r"https?://[^@]+@", "https://", current_remote)
            match = re.search(r"github\.com[:/](.+?)(?:\.git)?$", clean_url)
            if match:
                owner_repo = match.group(1).removesuffix(".git")
        except Exception:
            pass

        # Strategy 1: If GitHub token and repo detected, configure remote with token and push with credential.helper=
        if token and owner_repo:
            target_url = f"https://x-access-token:{token}@github.com/{owner_repo}.git"
            try:
                self._run(["remote", "set-url", remote, target_url])
            except Exception:
                pass

            cmd = ["-c", "credential.helper=", "push", "-u", remote, branch_name]
            if force:
                cmd.append("--force")
            try:
                return self._run(cmd, timeout=60)
            except GitError as ge:
                # Strategy 2: Push with Authorization header directly
                logger.debug(f"Direct push failed: {ge.stderr}. Retrying with Authorization header...")
                alt_url = f"https://github.com/{owner_repo}.git"
                alt_cmd = [
                    "-c", "credential.helper=",
                    "-c", f"http.extraHeader=Authorization: token {token}",
                    "push", "-u", alt_url, branch_name,
                ]
                if force:
                    alt_cmd.append("--force")
                try:
                    return self._run(alt_cmd, timeout=60)
                except GitError:
                    # Strategy 3: Push directly with username/token basic auth in target URL
                    pat_url = f"https://{token}@github.com/{owner_repo}.git"
                    pat_cmd = ["-c", "credential.helper=", "push", "-u", pat_url, branch_name]
                    if force:
                        pat_cmd.append("--force")
                    try:
                        return self._run(pat_cmd, timeout=60)
                    except GitError:
                        raise ge

        # Fallback standard push with credential.helper bypassed if token is present
        cmd = ["-c", "credential.helper=", "push", "-u", remote, branch_name]
        if force:
            cmd.append("--force")
        return self._run(cmd, timeout=60)

    def reset_hard(self):
        """Clean all uncommitted changes."""
        self._run(["reset", "--hard", "HEAD"])
        self._run(["clean", "-fd"])
