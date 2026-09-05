"""
GitHub Pull Request operations: creating PRs and posting review comments.
"""

import logging
from typing import Optional, Tuple
from oasis_agent.github_api.client import GitHubClientManager

logger = logging.getLogger("oasis_agent.pull_requests")


class PullRequestManager:
    """Creates and manages Pull Requests via PyGithub."""

    def __init__(self, client_mgr: GitHubClientManager):
        self.mgr = client_mgr

    def create_pull_request(
        self,
        repo_full_name: str,
        title: str,
        body: str,
        head_branch: str,
        base_branch: Optional[str] = None,
    ) -> Tuple[int, str]:
        """
        Create a GitHub Pull Request.
        Returns: (pr_number, pr_html_url)
        """
        def _create():
            repo = self.mgr.client.get_repo(repo_full_name)
            target_base = base_branch or repo.default_branch or "main"
            logger.info(f"Opening PR '{title}' from '{head_branch}' into '{target_base}' on {repo_full_name}...")
            pr = repo.create_pull(
                title=title,
                body=body,
                head=head_branch,
                base=target_base,
            )
            return pr.number, pr.html_url

        return self.mgr.execute_with_backoff(_create)

    def post_pr_comment(self, repo_full_name: str, pr_number: int, comment_body: str):
        """Post a review report comment on a pull request."""
        def _post():
            repo = self.mgr.client.get_repo(repo_full_name)
            pr = repo.get_pull(pr_number)
            return pr.create_issue_comment(comment_body)

        return self.mgr.execute_with_backoff(_post)

    def get_pull_request(self, repo_full_name: str, pr_number: int):
        """Fetch existing PR details."""
        def _get():
            repo = self.mgr.client.get_repo(repo_full_name)
            return repo.get_pull(pr_number)

        return self.mgr.execute_with_backoff(_get)
