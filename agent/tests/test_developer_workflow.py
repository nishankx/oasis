"""
Unit tests for Developer-Led Workflow: work, check, and push.
"""

import subprocess
from pathlib import Path
from oasis_agent.orchestrator import OasisAgentOrchestrator
from oasis_agent.config import OasisConfig, ProviderConfig, TaskRouting
from oasis_agent.models import RunStatus
from oasis_agent.llm.providers import OpenAICompatibleProvider


class MockSucceedingProvider(OpenAICompatibleProvider):
    def __init__(self, name: str, return_content: str):
        super().__init__(name, "http://mock", "mock-model", "fake-key")
        self.return_content = return_content
        self.call_count = 0

    def call_chat_completion(self, messages, temperature=0.2, max_tokens=None):
        self.call_count += 1
        return {"content": self.return_content, "duration_ms": 15, "model": self.model}


def init_source_repo(tmp_path: Path) -> Path:
    """Create a local git repository acting as remote origin."""
    src = tmp_path / "source_repo"
    src.mkdir()
    subprocess.run(["git", "init"], cwd=src, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Developer"], cwd=src, check=True)
    subprocess.run(["git", "config", "user.email", "dev@example.com"], cwd=src, check=True)

    # Initial file
    (src / "math_lib.py").write_text("def divide(a, b):\n    return a / b\n", encoding="utf-8")
    (src / "ISSUE_1.md").write_text("# Zero division bug\nHandle b == 0 in divide\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=src, check=True)
    subprocess.run(["git", "commit", "-m", "initial commit"], cwd=src, check=True)
    return src


def test_prepare_workspace(tmp_path):
    src_repo = init_source_repo(tmp_path)
    work_dir = tmp_path / "my_work"

    orchestrator = OasisAgentOrchestrator()
    res = orchestrator.prepare_workspace(
        repo_url_or_path=str(src_repo),
        issue_number=1,
        target_dir=str(work_dir),
    )

    assert res["dest_path"] == work_dir
    assert res["branch"] == "oasis-agent/fix-issue-1"
    assert (work_dir / ".git").exists()
    assert (work_dir / ".oasis-agent" / "issue.json").exists()


def test_evaluate_and_push_rejection_on_empty(tmp_path):
    src_repo = init_source_repo(tmp_path)
    work_dir = tmp_path / "my_work"

    orchestrator = OasisAgentOrchestrator()
    orchestrator.prepare_workspace(
        repo_url_or_path=str(src_repo),
        issue_number=1,
        target_dir=str(work_dir),
    )

    # Developer has made no changes yet
    report, exit_code = orchestrator.evaluate_and_push(
        repo_dir=str(work_dir),
        dry_run=True,
    )

    assert exit_code == 1
    assert "No changes detected" in report.meaningfulness.reasoning or "empty" in report.meaningfulness.reasoning.lower()


def test_evaluate_and_push_approved(tmp_path):
    src_repo = init_source_repo(tmp_path)
    work_dir = tmp_path / "my_work"

    # Set up mock config for evaluator
    config = OasisConfig(
        providers={"mock": ProviderConfig(base_url="http://mock", model="m", api_key_env="K")},
        llm_routing={"meaningfulness_judgment": TaskRouting(primary="mock")}
    )
    orchestrator = OasisAgentOrchestrator(config=config)
    mock_p = MockSucceedingProvider("mock", """
    {
      "meaningful": true,
      "confidence": 0.95,
      "reasoning": "Correctly prevents zero division",
      "missing_aspects": [],
      "dimension_scores": {
        "relevance": {"score": 0.95, "reasoning": "Direct fix"},
        "non_triviality": {"score": 0.9, "reasoning": "Guard added"},
        "correctness": {"score": 0.95, "reasoning": "Clean"},
        "closure_likelihood": {"score": 0.95, "reasoning": "Done"}
      },
      "risks_or_side_effects": [],
      "recommended_action": "APPROVE_AND_PR"
    }
    """)
    orchestrator.llm_client.router.register_custom_provider("mock", mock_p)

    orchestrator.prepare_workspace(
        repo_url_or_path=str(src_repo),
        issue_number=1,
        target_dir=str(work_dir),
    )

    # Developer writes code!
    (work_dir / "math_lib.py").write_text(
        "def divide(a, b):\n    if b == 0:\n        return 0.0\n    return a / b\n",
        encoding="utf-8",
    )

    # Developer tests or submits
    report, exit_code = orchestrator.evaluate_and_push(
        repo_dir=str(work_dir),
        dry_run=True,
    )

    assert exit_code == 0
    assert report.status == RunStatus.COMPLETED_DRY_RUN
    assert report.meaningfulness.meaningful is True
    assert report.meaningfulness.confidence >= 0.70
