"""
Unit tests for GitClient and BranchManager operations.
"""

import subprocess
from pathlib import Path
from oasis_agent.git_ops.client import GitClient
from oasis_agent.git_ops.branch_manager import BranchManager


def init_test_repo(tmp_path: Path) -> GitClient:
    """Initialize a bare minimum git repo for testing."""
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.name", "Tester"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "tester@test.com"], cwd=tmp_path, check=True)
    
    # Create initial commit
    readme = tmp_path / "README.md"
    readme.write_text("# Test Repo\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "initial commit"], cwd=tmp_path, check=True)
    
    return GitClient(tmp_path)


def test_git_branch_creation_and_diff(tmp_path):
    git = init_test_repo(tmp_path)
    branch_mgr = BranchManager(git, prefix="oasis-agent/fix-issue-")
    
    # Prepare issue branch
    branch_name = branch_mgr.prepare_issue_branch(42)
    assert branch_name == "oasis-agent/fix-issue-42"
    assert git.get_current_branch() == "oasis-agent/fix-issue-42"

    # Make modification
    readme = tmp_path / "README.md"
    readme.write_text("# Test Repo\nNew feature added.\n", encoding="utf-8")
    
    diff_summary = git.get_diff()
    assert "README.md" in diff_summary.files_changed
    assert diff_summary.insertions >= 1

    # Stage and commit
    git.stage_all()
    git.commit("fix(#42): update readme")

    # Cleanup / reset
    branch_mgr.cleanup_on_rejection()
    assert git.get_current_branch() in {"master", "main"}
