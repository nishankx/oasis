"""
Authenticated PyGithub client with automatic rate-limit backoff handling.
"""

import logging
import os
import time
from typing import Callable, Optional, TypeVar
from github import Github, RateLimitExceededException, GithubException

logger = logging.getLogger("oasis_agent.github_client")

T = TypeVar("T")


class GitHubClientManager:
    """Manages PyGithub client authentication and rate-limit retries."""

    def __init__(self, token: Optional[str] = None):
        self.token = token or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        self._gh: Optional[Github] = None

    @property
    def client(self) -> Github:
        if self._gh is None:
            if not self.token:
                logger.warning("No GITHUB_TOKEN configured. Unauthenticated GitHub API calls will be severely rate-limited.")
                self._gh = Github(timeout=30)
            else:
                from github import Auth
                self._gh = Github(auth=Auth.Token(self.token), timeout=30)
        return self._gh

    def execute_with_backoff(self, func: Callable[..., T], *args, max_retries: int = 3, **kwargs) -> T:
        """Execute a GitHub API call with exponential backoff on rate limits."""
        for attempt in range(max_retries + 1):
            try:
                return func(*args, **kwargs)
            except RateLimitExceededException as e:
                rl = self.client.get_rate_limit()
                rate_obj = getattr(rl, "rate", None) or getattr(getattr(rl, "resources", None), "core", None)
                reset_time = rate_obj.reset.timestamp() if rate_obj else time.time() + 60
                sleep_seconds = max(5, int(reset_time - time.time()) + 1)
                logger.warning(f"GitHub Primary Rate Limit exceeded. Sleeping for {sleep_seconds}s...")
                time.sleep(sleep_seconds)
            except GithubException as ge:
                if ge.status == 403 and "secondary rate limit" in str(ge.data).lower():
                    sleep_seconds = 10 * (attempt + 1)
                    logger.warning(f"GitHub Secondary Rate Limit hit. Backing off for {sleep_seconds}s...")
                    time.sleep(sleep_seconds)
                    continue
                raise
        raise RuntimeError("GitHub API calls failed after maximum backoff retries.")

    def get_rate_limit_info(self) -> dict:
        """Return rate limit info for status command."""
        if not self.token:
            return {"authenticated": False, "status": "No GITHUB_TOKEN configured"}
        try:
            rl = self.client.get_rate_limit()
            rate_obj = getattr(rl, "rate", None) or getattr(getattr(rl, "resources", None), "core", None)
            if rate_obj:
                return {
                    "authenticated": True,
                    "limit": rate_obj.limit,
                    "remaining": rate_obj.remaining,
                    "reset_time": rate_obj.reset.strftime("%Y-%m-%d %H:%M:%S UTC"),
                }
            return {"authenticated": True, "limit": "Unknown", "remaining": "Unknown", "reset_time": "Unknown"}
        except Exception as e:
            return {"authenticated": False, "status": f"Error fetching rate limit: {e}"}
