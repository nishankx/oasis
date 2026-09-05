"""
Unit and integration tests for Agent Gateway service.
"""

import subprocess
from pathlib import Path
import pytest
from oasis_agent.models import GitDiffSummary, IssueContext
from oasis_backend.services.agent_gateway import AgentGatewayService


@pytest.fixture
def repo_for_agent(tmp_path) -> Path:
    repo_dir = tmp_path / "agent_test_repo"
    repo_dir.mkdir()
    (repo_dir / "calculator.py").write_text(
        "def add(a, b):\n    # bug: returns multiplication\n    return a * b\n",
        encoding="utf-8",
    )
    (repo_dir / "requirements.txt").write_text("pytest>=8.0.0\n", encoding="utf-8")
    subprocess.run(["git", "init"], cwd=repo_dir, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.name", "Tester"], cwd=repo_dir, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo_dir, capture_output=True, check=True)
    subprocess.run(["git", "add", "."], cwd=repo_dir, capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo_dir, capture_output=True, check=True)
    return repo_dir


def test_agent_gateway_build_context(repo_for_agent):
    gateway = AgentGatewayService()
    issue_ctx = IssueContext(
        repo_url=str(repo_for_agent),
        repo_name="local/agent_test_repo",
        issue_number=1,
        title="Fix add function returning product instead of sum",
        body="The add function in calculator.py returns a * b instead of a + b.",
    )

    context = gateway.build_context(repo_for_agent, issue_ctx)
    assert "calculator.py" in context["relevant_files"]
    assert "Python" in context["tech_stack"]["languages"]


def test_agent_gateway_evaluate_diff_rejection(repo_for_agent):
    gateway = AgentGatewayService()
    issue_ctx = IssueContext(
        repo_url=str(repo_for_agent),
        repo_name="local/agent_test_repo",
        issue_number=1,
        title="Fix calculation bug",
        body="Calculator has a bug.",
    )
    # Empty or whitespace-only diff
    empty_diff = GitDiffSummary(files_changed=[], insertions=0, deletions=0, diff_content="")
    verdict = gateway.evaluate_diff(repo_for_agent, issue_ctx, empty_diff)
    assert verdict.meaningful is False
    assert verdict.recommended_action == "REJECT"
