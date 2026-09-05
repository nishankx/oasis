"""
Branch manager: handles branch naming conventions and cleanup.
"""

import logging
from typing import Optional
from oasis_agent.git_ops.client import GitClient

logger = logging.getLogger("oasis_agent.branch_manager")


class BranchManager:
    """Manages ephemeral git branches for issue remediation."""

    def __init__(self, git_client: GitClient, prefix: str = "oasis-agent/fix-issue-"):
        self.git = git_client
        self.prefix = prefix
        self.original_branch: Optional[str] = None
        self.active_branch: Optional[str] = None

    def get_branch_name_for_issue(self, issue_number: int) -> str:
        return f"{self.prefix}{issue_number}"

    def prepare_issue_branch(self, issue_number: int) -> str:
        """Record base branch and switch to a dedicated issue branch."""
        self.original_branch = self.git.get_current_branch()
        branch_name = self.get_branch_name_for_issue(issue_number)
        logger.info(f"Creating and switching to branch '{branch_name}' (from '{self.original_branch}')")
        self.git.create_and_checkout_branch(branch_name)
        self.active_branch = branch_name
        return branch_name

    def cleanup_on_rejection(self):
        """If changes are rejected, reset and return to the original branch."""
        logger.info("Cleaning up workspace and reverting to original branch...")
        try:
            self.git.reset_hard()
            if self.original_branch:
                self.git._run(["checkout", self.original_branch])
        except Exception as e:
            logger.warning(f"Error during branch cleanup: {e}")
