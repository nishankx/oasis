"""
Unit and integration tests for PR Service, Gatekeeper pre-push evaluation, and Webhook processing.
"""

import hashlib
import hmac
import json
import subprocess
from pathlib import Path
import pytest
from oasis_backend.config import settings
from oasis_backend.database.repositories.pr_repo import PullRequestRepository
from oasis_backend.database.repositories.scoring_repo import ScoringRepository
from oasis_backend.database.repositories.user_repo import UserRepository
from oasis_backend.database.repositories.workspace_repo import WorkspaceRepository
from oasis_backend.models.agent import GatekeeperVerdictResponse
from oasis_backend.services.agent_gateway import AgentGatewayService
from oasis_backend.services.auth_service import AuthService
from oasis_backend.services.pr_service import PRService
from oasis_backend.services.scoring_service import ScoringService
from oasis_backend.services.workspace_service import WorkspaceService


@pytest.fixture
def workspace_with_changes(tmp_path, db_conn, test_user) -> tuple[str, Path]:
    """Creates a local workspace session with staged edits."""
    ws_repo = WorkspaceRepository(db_conn)
    agent_gw = AgentGatewayService()
    ws_service = WorkspaceService(ws_repo, agent_gw)

    # Setup git repo
    repo_dir = tmp_path / "pr_test_project"
    repo_dir.mkdir()
    (repo_dir / "index.py").write_text("print('initial')\n", encoding="utf-8")
    subprocess.run(["git", "init"], cwd=repo_dir, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.name", "Tester"], cwd=repo_dir, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo_dir, capture_output=True, check=True)
    subprocess.run(["git", "add", "."], cwd=repo_dir, capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo_dir, capture_output=True, check=True)

    session = ws_service.prepare_workspace(
        user_id=test_user.id,
        repo_url=str(repo_dir),
        issue_number=55,
    )

    # Make code edit
    ws_service.write_file(session.id, "index.py", "print('initial')\nprint('fixed bug')\n", test_user.id)
    return session.id, repo_dir


def test_pre_push_gatekeeper_rejects_empty_diff(db_conn, test_user, tmp_path):
    import asyncio

    async def _run():
        ws_repo = WorkspaceRepository(db_conn)
        pr_repo = PullRequestRepository(db_conn)
        scoring_repo = ScoringRepository(db_conn)
        user_repo = UserRepository(db_conn)
        agent_gw = AgentGatewayService()
        auth_service = AuthService(user_repo)
        ws_service = WorkspaceService(ws_repo, agent_gw)
        scoring_service = ScoringService(scoring_repo)
        pr_service = PRService(pr_repo, ws_service, agent_gw, auth_service, scoring_service)

        # Git repo with initial commit but no workspace changes
        repo_dir = tmp_path / "empty_proj"
        repo_dir.mkdir()
        subprocess.run(["git", "init"], cwd=repo_dir, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Tester"], cwd=repo_dir, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo_dir, capture_output=True, check=True)
        (repo_dir / "README.md").write_text("# Initial\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=repo_dir, capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=repo_dir, capture_output=True, check=True)

        session = ws_service.prepare_workspace(user_id=test_user.id, repo_url=str(repo_dir), issue_number=1)

        res = await pr_service.evaluate_and_push(test_user.id, session.id)
        assert res.success is False
        assert res.status == "rejected"
        assert res.gatekeeper.meaningful is False
        assert "empty" in res.gatekeeper.reasoning.lower()

    asyncio.run(_run())


def test_pre_push_dry_run_approved(db_conn, test_user, workspace_with_changes, monkeypatch):
    import asyncio

    async def _run():
        ws_id, _ = workspace_with_changes
        ws_repo = WorkspaceRepository(db_conn)
        pr_repo = PullRequestRepository(db_conn)
        scoring_repo = ScoringRepository(db_conn)
        user_repo = UserRepository(db_conn)
        agent_gw = AgentGatewayService()
        auth_service = AuthService(user_repo)
        ws_service = WorkspaceService(ws_repo, agent_gw)
        scoring_service = ScoringService(scoring_repo)
        pr_service = PRService(pr_repo, ws_service, agent_gw, auth_service, scoring_service)

        # Mock gatekeeper verdict to APPROVE
        monkeypatch.setattr(
            agent_gw,
            "evaluate_diff",
            lambda *args, **kwargs: GatekeeperVerdictResponse(
                meaningful=True,
                confidence=0.92,
                reasoning="Valid remediation patch.",
                recommended_action="APPROVE_AND_PR",
            ),
        )

        res = await pr_service.evaluate_and_push(test_user.id, ws_id, dry_run=True)
        assert res.success is True
        assert res.status == "dry_run"
        assert res.gatekeeper.confidence == 0.92

    asyncio.run(_run())


def test_pre_push_force_bypasses_rejection(db_conn, test_user, workspace_with_changes, monkeypatch):
    import asyncio

    async def _run():
        ws_id, _ = workspace_with_changes
        ws_repo = WorkspaceRepository(db_conn)
        pr_repo = PullRequestRepository(db_conn)
        scoring_repo = ScoringRepository(db_conn)
        user_repo = UserRepository(db_conn)
        agent_gw = AgentGatewayService()
        auth_service = AuthService(user_repo)
        ws_service = WorkspaceService(ws_repo, agent_gw)
        scoring_service = ScoringService(scoring_repo)
        pr_service = PRService(pr_repo, ws_service, agent_gw, auth_service, scoring_service)

        # Mock gatekeeper verdict to REJECT
        monkeypatch.setattr(
            agent_gw,
            "evaluate_diff",
            lambda *args, **kwargs: GatekeeperVerdictResponse(
                meaningful=False,
                confidence=0.15,
                reasoning="Trivial changes.",
                recommended_action="REJECT",
            ),
        )

        # Without force -> rejected
        res_normal = await pr_service.evaluate_and_push(test_user.id, ws_id, dry_run=True, force=False)
        assert res_normal.success is False
        assert res_normal.status == "rejected"

        # With force -> dry_run succeeds despite rejection
        res_forced = await pr_service.evaluate_and_push(test_user.id, ws_id, dry_run=True, force=True)
        assert res_forced.success is True
        assert res_forced.status == "dry_run"

    asyncio.run(_run())


def test_webhook_pr_merged_triggers_scoring(db_conn, test_user):
    import asyncio

    async def _run():
        pr_repo = PullRequestRepository(db_conn)
        scoring_repo = ScoringRepository(db_conn)
        scoring_service = ScoringService(scoring_repo)
        agent_gw = AgentGatewayService()
        ws_repo = WorkspaceRepository(db_conn)
        ws_service = WorkspaceService(ws_repo, agent_gw)
        user_repo = UserRepository(db_conn)
        auth_service = AuthService(user_repo)
        pr_service = PRService(pr_repo, ws_service, agent_gw, auth_service, scoring_service)

        # Create tracked PR record
        pr_rec = pr_repo.create(
            pr_id="pr_webhook_test_1",
            workspace_id=None,
            user_id=test_user.id,
            repo_full_name="oasis/webhook-target",
            pr_number=33,
            pr_url="https://github.com/oasis/webhook-target/pull/33",
            head_branch="oasis-agent/fix-issue-33",
        )

        # Simulate GitHub pull_request.closed with merged: true
        webhook_payload = {
            "action": "closed",
            "repository": {"full_name": "oasis/webhook-target", "stargazers_count": 350},
            "pull_request": {"number": 33, "merged": True, "additions": 25, "deletions": 5},
        }

        res = await pr_service.handle_github_webhook("pull_request", webhook_payload)
        assert res["handled"] is True
        assert res["action"] == "merged_and_scored"
        assert res["score_awarded"] > 100

        # Verify PR status updated to merged
        updated_pr = pr_repo.get_by_id(pr_rec.pr_id)
        assert updated_pr is not None
        assert updated_pr.status == "merged"
        assert updated_pr.merged_at is not None

    asyncio.run(_run())


def test_api_webhook_signature_verification(client):
    secret = settings.github_webhook_secret
    payload = json.dumps({"action": "ping"}).encode("utf-8")
    valid_sig = "sha256=" + hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()

    # Valid signature
    resp = client.post(
        "/api/v1/webhooks/github",
        content=payload,
        headers={"X-GitHub-Event": "ping", "X-Hub-Signature-256": valid_sig},
    )
    assert resp.status_code == 200

    # Invalid signature
    resp_bad = client.post(
        "/api/v1/webhooks/github",
        content=payload,
        headers={"X-GitHub-Event": "ping", "X-Hub-Signature-256": "sha256=invalid_hash"},
    )
    assert resp_bad.status_code == 401
