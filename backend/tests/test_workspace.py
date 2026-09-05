"""
Unit and integration tests for Workspace service and Monaco editor file support.
"""

import os
import subprocess
from pathlib import Path
import pytest
from oasis_backend.database.repositories.workspace_repo import WorkspaceRepository
from oasis_backend.services.agent_gateway import AgentGatewayService
from oasis_backend.services.workspace_service import WorkspaceService


@pytest.fixture
def sample_local_repo(tmp_path) -> Path:
    """Creates a local git repository on disk for workspace tests."""
    repo_dir = tmp_path / "sample_git_project"
    repo_dir.mkdir()
    (repo_dir / "src").mkdir()
    (repo_dir / "src" / "main.py").write_text("def hello():\n    return 'world'\n", encoding="utf-8")
    (repo_dir / "README.md").write_text("# Sample Project\n", encoding="utf-8")

    subprocess.run(["git", "init"], cwd=repo_dir, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.name", "Tester"], cwd=repo_dir, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo_dir, capture_output=True, check=True)
    subprocess.run(["git", "add", "."], cwd=repo_dir, capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "initial commit"], cwd=repo_dir, capture_output=True, check=True)
    return repo_dir


def test_prepare_workspace_and_tree(db_conn, test_user, sample_local_repo):
    ws_repo = WorkspaceRepository(db_conn)
    agent_gw = AgentGatewayService()
    ws_service = WorkspaceService(ws_repo, agent_gw)

    session = ws_service.prepare_workspace(
        user_id=test_user.id,
        repo_url=str(sample_local_repo),
        issue_number=10,
    )
    assert session.user_id == test_user.id
    assert session.issue_number == 10
    assert "oasis-agent/fix-issue-10" in session.branch_name

    tree = ws_service.build_file_tree(session.id, test_user.id)
    assert any(n.name == "src" and n.is_dir for n in tree)
    assert any(n.name == "README.md" and not n.is_dir for n in tree)


def test_workspace_file_read_and_write(db_conn, test_user, sample_local_repo):
    ws_repo = WorkspaceRepository(db_conn)
    agent_gw = AgentGatewayService()
    ws_service = WorkspaceService(ws_repo, agent_gw)

    session = ws_service.prepare_workspace(
        user_id=test_user.id,
        repo_url=str(sample_local_repo),
        issue_number=11,
    )

    # Read file
    file_data = ws_service.read_file(session.id, "src/main.py", test_user.id)
    assert "def hello():" in file_data.content

    # Write file
    new_content = "def hello():\n    return 'oasis-fixed'\n"
    save_resp = ws_service.write_file(session.id, "src/main.py", new_content, test_user.id)
    assert save_resp.saved is True

    # Re-read
    updated_data = ws_service.read_file(session.id, "src/main.py", test_user.id)
    assert "oasis-fixed" in updated_data.content

    # Check diff
    diff_resp = ws_service.get_diff(session.id, test_user.id)
    assert "oasis-fixed" in diff_resp.diff
    assert diff_resp.insertions > 0


def test_workspace_path_traversal_protection(db_conn, test_user, sample_local_repo):
    ws_repo = WorkspaceRepository(db_conn)
    agent_gw = AgentGatewayService()
    ws_service = WorkspaceService(ws_repo, agent_gw)

    session = ws_service.prepare_workspace(
        user_id=test_user.id,
        repo_url=str(sample_local_repo),
        issue_number=12,
    )

    # Attempt to read outside workspace
    with pytest.raises(ValueError, match="Security violation"):
        ws_service.read_file(session.id, "../../outside.txt", test_user.id)

    with pytest.raises(ValueError, match="Security violation"):
        ws_service.write_file(session.id, "../escape.txt", "attack", test_user.id)


def test_workspace_cleanup(db_conn, test_user, sample_local_repo):
    ws_repo = WorkspaceRepository(db_conn)
    agent_gw = AgentGatewayService()
    ws_service = WorkspaceService(ws_repo, agent_gw)

    session = ws_service.prepare_workspace(
        user_id=test_user.id,
        repo_url=str(sample_local_repo),
        issue_number=13,
    )
    _, local_path = ws_service.get_workspace_or_404(session.id, test_user.id)
    assert local_path.exists()

    res = ws_service.cleanup_workspace(session.id)
    assert res is True
    assert not local_path.exists()


def test_api_workspace_endpoints(client, auth_headers, sample_local_repo):
    # 1. Prepare
    prep_resp = client.post(
        "/api/v1/workspace/prepare",
        json={"repo_url": str(sample_local_repo), "issue_number": 20},
        headers=auth_headers,
    )
    assert prep_resp.status_code == 201
    ws_id = prep_resp.json()["id"]

    # 2. File tree
    tree_resp = client.get(f"/api/v1/workspace/{ws_id}/tree", headers=auth_headers)
    assert tree_resp.status_code == 200
    assert len(tree_resp.json()) > 0

    # 3. Read file
    read_resp = client.get(f"/api/v1/workspace/{ws_id}/file?path=src/main.py", headers=auth_headers)
    assert read_resp.status_code == 200
    assert "def hello" in read_resp.json()["content"]

    # 4. Save file
    save_resp = client.put(
        f"/api/v1/workspace/{ws_id}/file",
        json={"path": "src/main.py", "content": "# Updated via Monaco API"},
        headers=auth_headers,
    )
    assert save_resp.status_code == 200
    assert save_resp.json()["saved"] is True

    # 5. Diff
    diff_resp = client.get(f"/api/v1/workspace/{ws_id}/diff", headers=auth_headers)
    assert diff_resp.status_code == 200
    assert "Updated via Monaco API" in diff_resp.json()["diff"]

    # 6. Delete
    del_resp = client.delete(f"/api/v1/workspace/{ws_id}", headers=auth_headers)
    assert del_resp.status_code == 200
