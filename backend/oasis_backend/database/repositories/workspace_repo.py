"""
Workspace database repository.
"""

from __future__ import annotations
import datetime
import json
import sqlite3
from typing import List, Optional
from oasis_backend.models.workspace import WorkspaceSession


class WorkspaceRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def create(
        self,
        workspace_id: str,
        user_id: int,
        repo_url: str,
        repo_full_name: str,
        issue_number: int,
        branch_name: str,
        local_path: str,
        relevant_files: List[str],
    ) -> WorkspaceSession:
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO workspaces (
                id, user_id, repo_url, repo_full_name, issue_number,
                branch_name, local_path, relevant_files_json, status,
                created_at, last_accessed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?)
            """,
            (
                workspace_id,
                user_id,
                repo_url,
                repo_full_name,
                issue_number,
                branch_name,
                local_path,
                json.dumps(relevant_files),
                now,
                now,
            ),
        )
        return WorkspaceSession(
            id=workspace_id,
            user_id=user_id,
            repo_url=repo_url,
            repo_full_name=repo_full_name,
            issue_number=issue_number,
            branch_name=branch_name,
            relevant_files=relevant_files,
            status="active",
            created_at=now,
            last_accessed_at=now,
        )

    def get_by_id(self, workspace_id: str) -> Optional[tuple[WorkspaceSession, str]]:
        """Returns (WorkspaceSession, local_path)"""
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT id, user_id, repo_url, repo_full_name, issue_number, branch_name,
                   local_path, relevant_files_json, status, created_at, last_accessed_at
            FROM workspaces WHERE id = ?
            """,
            (workspace_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        session = WorkspaceSession(
            id=row["id"],
            user_id=row["user_id"],
            repo_url=row["repo_url"],
            repo_full_name=row["repo_full_name"],
            issue_number=row["issue_number"],
            branch_name=row["branch_name"],
            relevant_files=json.loads(row["relevant_files_json"] or "[]"),
            status=row["status"],
            created_at=row["created_at"],
            last_accessed_at=row["last_accessed_at"],
        )
        return session, row["local_path"]

    def touch(self, workspace_id: str) -> None:
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        cur = self.conn.cursor()
        cur.execute(
            "UPDATE workspaces SET last_accessed_at = ? WHERE id = ?",
            (now, workspace_id),
        )

    def update_status(self, workspace_id: str, status: str) -> None:
        cur = self.conn.cursor()
        cur.execute(
            "UPDATE workspaces SET status = ? WHERE id = ?",
            (status, workspace_id),
        )

    def list_by_user(self, user_id: int) -> List[WorkspaceSession]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT id, user_id, repo_url, repo_full_name, issue_number, branch_name,
                   relevant_files_json, status, created_at, last_accessed_at
            FROM workspaces
            WHERE user_id = ? AND status != 'deleted'
            ORDER BY last_accessed_at DESC
            """,
            (user_id,),
        )
        results = []
        for row in cur.fetchall():
            results.append(
                WorkspaceSession(
                    id=row["id"],
                    user_id=row["user_id"],
                    repo_url=row["repo_url"],
                    repo_full_name=row["repo_full_name"],
                    issue_number=row["issue_number"],
                    branch_name=row["branch_name"],
                    relevant_files=json.loads(row["relevant_files_json"] or "[]"),
                    status=row["status"],
                    created_at=row["created_at"],
                    last_accessed_at=row["last_accessed_at"],
                )
            )
        return results

    def get_idle_workspaces(self, max_idle_hours: int = 2) -> List[tuple[str, str]]:
        """Returns list of (workspace_id, local_path) for active workspaces older than max_idle_hours."""
        cur = self.conn.cursor()
        cutoff = (
            datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=max_idle_hours)
        ).isoformat()
        cur.execute(
            """
            SELECT id, local_path FROM workspaces
            WHERE status = 'active' AND last_accessed_at < ?
            """,
            (cutoff,),
        )
        return [(r["id"], r["local_path"]) for r in cur.fetchall()]
