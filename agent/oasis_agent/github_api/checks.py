"""
GitHub Actions check runs and commit status monitor.
"""

import logging
import time
from typing import Dict, List, Optional
from oasis_agent.github_api.client import GitHubClientManager

logger = logging.getLogger("oasis_agent.checks")


class ChecksMonitor:
    """Monitors CI check runs triggered on pull requests."""

    def __init__(self, client_mgr: GitHubClientManager):
        self.mgr = client_mgr

    def get_commit_check_runs(self, repo_full_name: str, commit_sha: str) -> List[Dict[str, any]]:
        """Fetch check runs associated with a commit SHA."""
        def _fetch():
            repo = self.mgr.client.get_repo(repo_full_name)
            commit = repo.get_commit(commit_sha)
            check_runs = commit.get_check_runs()
            runs = []
            for cr in check_runs:
                runs.append({
                    "name": cr.name,
                    "status": cr.status,
                    "conclusion": cr.conclusion,
                    "url": cr.html_url,
                })
            return runs

        try:
            return self.mgr.execute_with_backoff(_fetch)
        except Exception as e:
            logger.debug(f"Failed to fetch check runs for {commit_sha}: {e}")
            return []

    def poll_for_completion(
        self,
        repo_full_name: str,
        commit_sha: str,
        timeout_seconds: int = 90,
        poll_interval: int = 15,
    ) -> Optional[str]:
        """
        Poll check runs until completion or timeout.
        Returns final overall status string (e.g. 'success', 'failure', or 'in_progress').
        """
        start = time.time()
        logger.info(f"Polling CI status for commit {commit_sha[:8]} (timeout={timeout_seconds}s)...")

        while time.time() - start < timeout_seconds:
            runs = self.get_commit_check_runs(repo_full_name, commit_sha)
            if not runs:
                time.sleep(poll_interval)
                continue

            all_completed = all(r["status"] == "completed" for r in runs)
            if all_completed:
                conclusions = [r["conclusion"] for r in runs]
                if any(c in {"failure", "timed_out", "action_required"} for c in conclusions):
                    return "failure"
                if all(c in {"success", "neutral", "skipped"} for c in conclusions):
                    return "success"
                return "completed"

            time.sleep(poll_interval)

        return "in_progress"
