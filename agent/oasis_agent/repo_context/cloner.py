"""
Git repository cloner with shallow clone default, full clone fallback,
and local directory caching (.oasis-agent/cache/).
"""

import logging
import os
import re
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger("oasis_agent.cloner")


class RepoCloner:
    """Clones and caches remote git repositories locally."""

    def __init__(self, cache_dir: str = ".oasis-agent/cache", shallow: bool = True):
        self.cache_dir = Path(cache_dir).resolve()
        self.shallow = shallow
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def parse_repo_identifier(repo_str: str) -> tuple[str, str]:
        """Extract (owner, repo_name) from URL or 'owner/repo' format."""
        # Clean trailing slash or .git
        cleaned = repo_str.rstrip("/").removesuffix(".git")
        match = re.search(r"github\.com[:/]([^/]+)/([^/]+)$", cleaned, re.IGNORECASE)
        if match:
            return match.group(1), match.group(2)
        local_p = Path(cleaned)
        if local_p.exists():
            return "local", re.sub(r"[^\w\-]", "_", local_p.name) or "repo"

        parts = cleaned.split("/")
        if len(parts) == 2:
            return parts[0], parts[1]
        # Return fallback for local folders or generic names
        safe_name = re.sub(r"[^\w\-]", "_", Path(cleaned).name)
        return "local", safe_name or "repo"

    def get_authenticated_url(self, repo_url: str, token: Optional[str] = None) -> str:
        """Inject GitHub token into HTTPS URL if available."""
        if not token:
            token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if not token or not repo_url.startswith("https://"):
            return repo_url
        # Insert token into https:// URL
        if "@" not in repo_url:
            return repo_url.replace("https://", f"https://x-access-token:{token}@")
        return repo_url

    def clone_or_get_cached(self, repo_url_or_path: str) -> Path:
        """
        Check if repo is cached; if not, clone shallowly (or full clone on fallback).
        If already a local path, returns it directly.
        """
        local_path = Path(repo_url_or_path)
        if local_path.exists() and (local_path / ".git").exists():
            logger.info(f"Using existing local repository at {local_path}")
            return local_path

        owner, repo_name = self.parse_repo_identifier(repo_url_or_path)
        target_dir = self.cache_dir / f"{owner}_{repo_name}"

        if (target_dir / ".git").exists():
            logger.info(f"Found cached repository at {target_dir}")
            # Quick fetch to ensure up-to-date
            try:
                subprocess.run(
                    ["git", "fetch", "--depth=1"],
                    cwd=target_dir,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=30,
                )
            except Exception as e:
                logger.debug(f"Cache refresh skipped: {e}")
            return target_dir

        target_dir.parent.mkdir(parents=True, exist_ok=True)
        clone_url = self.get_authenticated_url(repo_url_or_path)

        # 1. Attempt shallow clone
        clone_cmd = ["git", "clone"]
        if self.shallow:
            clone_cmd.extend(["--depth", "1"])
        clone_cmd.extend([clone_url, str(target_dir)])

        logger.info(f"Cloning {owner}/{repo_name} to {target_dir} (shallow={self.shallow})...")
        res = subprocess.run(clone_cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")

        if res.returncode != 0:
            logger.warning(
                f"Shallow clone failed (code {res.returncode}): {(res.stderr or '')[:200]}. Retrying with full clone..."
            )
            # 2. Fallback to full clone
            fallback_cmd = ["git", "clone", clone_url, str(target_dir)]
            fallback_res = subprocess.run(fallback_cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
            if fallback_res.returncode != 0:
                raise RuntimeError(
                    f"Failed to clone repository '{repo_url_or_path}': {(fallback_res.stderr or '').strip()}"
                )

        logger.info(f"Successfully cloned repository to {target_dir}")
        return target_dir
