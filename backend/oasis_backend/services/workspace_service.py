"""
Workspace service: manages ephemeral sandbox sessions, Monaco editor file operations, and AI diffs.
"""

from __future__ import annotations
import datetime
import json
import os
import shutil
import stat
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
from oasis_agent.git_ops import BranchManager, GitClient
from oasis_agent.models import GitDiffSummary, IssueContext
from oasis_agent.repo_context.cloner import RepoCloner
from oasis_backend.config import settings
from oasis_backend.database.repositories.workspace_repo import WorkspaceRepository
from oasis_backend.models.workspace import (
    FileContentResponse,
    FileNode,
    SaveFileResponse,
    WorkspaceDiffResponse,
    WorkspaceSession,
)
from oasis_backend.services.agent_gateway import AgentGatewayService

IGNORED_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".venv",
    "venv",
    "dist",
    "build",
    ".oasis-agent",
    ".idea",
    ".vscode",
}

IGNORED_EXTENSIONS = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".pdf",
    ".zip",
    ".tar",
    ".gz",
    ".exe",
    ".dll",
    ".so",
}


class WorkspaceService:
    def __init__(
        self,
        workspace_repo: WorkspaceRepository,
        agent_gateway: AgentGatewayService,
    ):
        self.workspace_repo = workspace_repo
        self.agent_gateway = agent_gateway

    def _resolve_safe_file_path(self, base_dir: Path, rel_path: str) -> Path:
        """Ensures rel_path is resolved strictly inside base_dir to avoid path traversal."""
        clean_path = rel_path.lstrip("/\\")
        target = (base_dir / clean_path).resolve()
        if not str(target).startswith(str(base_dir.resolve())):
            raise ValueError(f"Security violation: Access denied for path '{rel_path}' outside workspace.")
        return target

    def prepare_workspace(
        self,
        user_id: int,
        repo_url: str,
        issue_number: int,
        github_token: Optional[str] = None,
        issue_title: Optional[str] = None,
        issue_body: Optional[str] = None,
    ) -> WorkspaceSession:
        """
        Creates an isolated ephemeral workspace, clones the repo, checks out issue branch,
        extracts context & relevant files via oasis-agent, and stores the session.
        """
        workspace_id = f"ws_{uuid.uuid4().hex[:12]}"
        owner, repo_name = RepoCloner.parse_repo_identifier(repo_url)
        full_repo_name = f"{owner}/{repo_name}"

        workspaces_base = settings.resolve_workspaces_dir()
        local_path = (workspaces_base / workspace_id).resolve()
        local_path.mkdir(parents=True, exist_ok=True)

        # Clone repository
        cloner = RepoCloner(shallow=False)
        auth_url = cloner.get_authenticated_url(repo_url, token=github_token)

        # If repo is already a local directory on disk (e.g. for testing), copy it
        if Path(repo_url).exists() and (Path(repo_url) / ".git").exists():
            shutil.copytree(repo_url, local_path, dirs_exist_ok=True)
        else:
            import subprocess
            res = subprocess.run(
                ["git", "clone", auth_url, str(local_path)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=120,
            )
            if res.returncode != 0:
                # Cleanup on clone failure
                self._safe_rmtree(local_path)
                raise RuntimeError(f"Git clone failed: {(res.stderr or '').strip()}")

        # Setup git branch
        git_client = GitClient(local_path)
        branch_mgr = BranchManager(git_client)
        branch_name = branch_mgr.prepare_issue_branch(issue_number)

        # Setup Issue Context
        issue_ctx = IssueContext(
            repo_url=repo_url,
            repo_name=full_repo_name,
            issue_number=issue_number,
            title=issue_title or f"Issue #{issue_number}",
            body=issue_body or f"Target issue #{issue_number} for Oasis platform resolution.",
        )

        # Persist issue metadata in .oasis-agent/issue.json
        meta_dir = local_path / ".oasis-agent"
        meta_dir.mkdir(parents=True, exist_ok=True)
        (meta_dir / "issue.json").write_text(issue_ctx.model_dump_json(indent=2), encoding="utf-8")

        # Extract context & relevant files via oasis-agent
        context_data = self.agent_gateway.build_context(local_path, issue_ctx)
        relevant_files = context_data.get("relevant_files", [])

        # Store session in DB
        session = self.workspace_repo.create(
            workspace_id=workspace_id,
            user_id=user_id,
            repo_url=repo_url,
            repo_full_name=full_repo_name,
            issue_number=issue_number,
            branch_name=branch_name,
            local_path=str(local_path),
            relevant_files=relevant_files,
        )

        return session

    def get_workspace_or_404(self, workspace_id: str, user_id: Optional[int] = None) -> tuple[WorkspaceSession, Path]:
        record = self.workspace_repo.get_by_id(workspace_id)
        if not record:
            raise KeyError(f"Workspace '{workspace_id}' not found.")
        session, path_str = record
        if user_id is not None and session.user_id != user_id:
            raise PermissionError("You do not have permission to access this workspace.")
        local_path = Path(path_str)
        if not local_path.exists():
            raise FileNotFoundError(f"Workspace directory for '{workspace_id}' no longer exists on disk.")
        self.workspace_repo.touch(workspace_id)
        return session, local_path

    def build_file_tree(self, workspace_id: str, user_id: Optional[int] = None) -> List[FileNode]:
        """Generates a hierarchical file tree for Monaco editor navigation."""
        _, local_path = self.get_workspace_or_404(workspace_id, user_id)

        def _traverse(cur_dir: Path) -> List[FileNode]:
            nodes: List[FileNode] = []
            try:
                entries = sorted(cur_dir.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
            except Exception:
                return nodes

            for entry in entries:
                if entry.name in IGNORED_DIRS or entry.name.startswith("."):
                    continue
                rel = str(entry.relative_to(local_path)).replace("\\", "/")
                if entry.is_dir():
                    children = _traverse(entry)
                    nodes.append(FileNode(name=entry.name, path=rel, is_dir=True, children=children))
                else:
                    if entry.suffix.lower() in IGNORED_EXTENSIONS:
                        continue
                    try:
                        size = entry.stat().st_size
                    except Exception:
                        size = 0
                    nodes.append(FileNode(name=entry.name, path=rel, is_dir=False, size_bytes=size))
            return nodes

        return _traverse(local_path)

    def read_file(self, workspace_id: str, rel_path: str, user_id: Optional[int] = None) -> FileContentResponse:
        """Reads file content from workspace directory."""
        _, local_path = self.get_workspace_or_404(workspace_id, user_id)
        target_file = self._resolve_safe_file_path(local_path, rel_path)
        if not target_file.exists() or target_file.is_dir():
            raise FileNotFoundError(f"File '{rel_path}' not found in workspace.")

        try:
            content = target_file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # Fallback for binary / non-utf8
            content = target_file.read_text(encoding="latin-1")

        return FileContentResponse(
            path=rel_path.replace("\\", "/"),
            content=content,
            size_bytes=len(content.encode("utf-8")),
        )

    def write_file(
        self,
        workspace_id: str,
        rel_path: str,
        content: str,
        user_id: Optional[int] = None,
    ) -> SaveFileResponse:
        """Writes content to file in workspace."""
        _, local_path = self.get_workspace_or_404(workspace_id, user_id)
        target_file = self._resolve_safe_file_path(local_path, rel_path)
        target_file.parent.mkdir(parents=True, exist_ok=True)

        target_file.write_text(content, encoding="utf-8")
        return SaveFileResponse(
            path=rel_path.replace("\\", "/"),
            saved=True,
            bytes_written=len(content.encode("utf-8")),
        )

    def get_diff(self, workspace_id: str, user_id: Optional[int] = None) -> WorkspaceDiffResponse:
        """Calculates current git diff against original base branch."""
        _, local_path = self.get_workspace_or_404(workspace_id, user_id)
        git_client = GitClient(local_path)

        base_branch = "main"
        for cand in ["main", "master"]:
            try:
                git_client._run(["rev-parse", "--verify", cand])
                base_branch = cand
                break
            except Exception:
                pass

        diff_summary: GitDiffSummary = git_client.get_diff(base=base_branch)
        if not diff_summary.diff_content.strip():
            diff_summary = git_client.get_diff()  # Uncommitted changes

        return WorkspaceDiffResponse(
            diff=diff_summary.diff_content,
            files_changed=diff_summary.files_changed,
            insertions=diff_summary.insertions,
            deletions=diff_summary.deletions,
        )

    def apply_ai_fix(
        self,
        workspace_id: str,
        instruction: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Generates AI fix via agent gateway and returns proposal."""
        session, local_path = self.get_workspace_or_404(workspace_id, user_id)

        # Load issue context
        issue_file = local_path / ".oasis-agent" / "issue.json"
        if issue_file.exists():
            issue_ctx = IssueContext.model_validate_json(issue_file.read_text(encoding="utf-8"))
        else:
            issue_ctx = IssueContext(
                repo_url=session.repo_url,
                repo_name=session.repo_full_name,
                issue_number=session.issue_number,
                title=f"Issue #{session.issue_number}",
                body="Workspace issue context.",
            )

        return self.agent_gateway.suggest_fix(local_path, issue_ctx, instruction)

    def cleanup_workspace(self, workspace_id: str) -> bool:
        """Deletes workspace folder from disk and updates DB status."""
        record = self.workspace_repo.get_by_id(workspace_id)
        if not record:
            return False
        _, path_str = record
        local_path = Path(path_str)
        self._safe_rmtree(local_path)
        self.workspace_repo.update_status(workspace_id, "deleted")
        return True

    def reap_idle_workspaces(self, max_idle_hours: int = 2) -> int:
        """Deletes all workspaces idle longer than max_idle_hours."""
        idle = self.workspace_repo.get_idle_workspaces(max_idle_hours)
        count = 0
        for ws_id, path_str in idle:
            try:
                self._safe_rmtree(Path(path_str))
                self.workspace_repo.update_status(ws_id, "deleted")
                count += 1
            except Exception:
                pass
        return count

    @staticmethod
    def _safe_rmtree(path: Path) -> None:
        """Safely removes directory tree including Windows read-only git files."""
        if not path.exists():
            return

        def _remove_readonly(func, p, _):
            try:
                os.chmod(p, stat.S_IWRITE)
                func(p)
            except Exception:
                pass

        rmtree_kwargs = (
            {"onexc": _remove_readonly}
            if sys.version_info >= (3, 12)
            else {"onerror": _remove_readonly}
        )

        try:
            shutil.rmtree(path, **rmtree_kwargs)
        except Exception:
            pass
