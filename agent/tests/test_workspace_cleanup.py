"""
Unit tests for automatic workspace cleanup after Pull Request creation.
"""

import os
import stat
from pathlib import Path
from rich.console import Console
from oasis_agent.orchestrator import OasisAgentOrchestrator


def test_cleanup_workspace_deletes_tree(tmp_path):
    # Setup mock workspace with subfolders and read-only files (simulating .git)
    repo_dir = tmp_path / "mock_cloned_repo"
    repo_dir.mkdir()
    (repo_dir / "src").mkdir()
    (repo_dir / "src" / "index.js").write_text("console.log('hello');", encoding="utf-8")
    
    git_dir = repo_dir / ".git" / "objects"
    git_dir.mkdir(parents=True)
    pack_file = git_dir / "sample.pack"
    pack_file.write_bytes(b"dummy pack content")
    # Make read-only
    os.chmod(pack_file, stat.S_IREAD)

    assert repo_dir.exists()

    console = Console(record=True)
    res = OasisAgentOrchestrator.cleanup_workspace(repo_dir, console=console)

    assert res is True
    assert not repo_dir.exists()


def test_cleanup_workspace_protects_home_and_package(monkeypatch):
    home = Path.home()
    console = Console(record=True)
    res = OasisAgentOrchestrator.cleanup_workspace(home, console=console)
    assert res is False
    assert home.exists()
