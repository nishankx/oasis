"""
GitHub Issues operations: fetching issue details and posting comments.
"""

import logging
from typing import Optional
from oasis_agent.models import IssueContext
from oasis_agent.github_api.client import GitHubClientManager

logger = logging.getLogger("oasis_agent.issues")


class IssueManager:
    """Interacts with GitHub Issues."""

    def __init__(self, client_mgr: GitHubClientManager):
        self.mgr = client_mgr

    def get_issue(self, repo_full_name: str, issue_number: int) -> IssueContext:
        """Fetch issue details, labels, and comments from GitHub."""
        def _fetch():
            repo = self.mgr.client.get_repo(repo_full_name)
            issue = repo.get_issue(number=issue_number)
            labels = [l.name for l in issue.labels]
            comments = [c.body for c in issue.get_comments()]
            return IssueContext(
                repo_url=repo.html_url,
                repo_name=repo_full_name,
                issue_number=issue.number,
                title=issue.title,
                body=issue.body or "",
                labels=labels,
                comments=comments,
                author=issue.user.login if issue.user else None,
            )

        return self.mgr.execute_with_backoff(_fetch)

    def post_comment(self, repo_full_name: str, issue_number: int, comment_body: str):
        """Post a comment on an issue (e.g. rejection explanation report)."""
        def _post():
            repo = self.mgr.client.get_repo(repo_full_name)
            issue = repo.get_issue(number=issue_number)
            return issue.create_comment(comment_body)

        return self.mgr.execute_with_backoff(_post)
