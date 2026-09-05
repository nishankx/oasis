"""
Pull Request database repository.
"""

from __future__ import annotations
import datetime
import json
import sqlite3
from typing import Any, Dict, List, Optional
from oasis_backend.models.pr import PRStatusResponse


class PullRequestRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def create(
        self,
        pr_id: str,
        workspace_id: Optional[str],
        user_id: int,
        repo_full_name: str,
        pr_number: int,
        pr_url: str,
        head_branch: str,
        base_branch: str = "main",
        gatekeeper_verdict: Optional[Dict[str, Any]] = None,
        status: str = "open",
        ci_status: Optional[str] = None,
    ) -> PRStatusResponse:
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO pull_requests (
                id, workspace_id, user_id, repo_full_name, pr_number, pr_url,
                head_branch, base_branch, gatekeeper_verdict_json, status,
                ci_status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                pr_id,
                workspace_id,
                user_id,
                repo_full_name,
                pr_number,
                pr_url,
                head_branch,
                base_branch,
                json.dumps(gatekeeper_verdict) if gatekeeper_verdict else None,
                status,
                ci_status,
                now,
                now,
            ),
        )
        return PRStatusResponse(
            pr_id=pr_id,
            workspace_id=workspace_id,
            repo_full_name=repo_full_name,
            pr_number=pr_number,
            pr_url=pr_url,
            head_branch=head_branch,
            status=status,
            ci_status=ci_status,
            gatekeeper=gatekeeper_verdict,
            created_at=now,
            updated_at=now,
        )

    def get_by_id(self, pr_id: str) -> Optional[PRStatusResponse]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT id, workspace_id, user_id, repo_full_name, pr_number, pr_url,
                   head_branch, status, ci_status, merged_at, gatekeeper_verdict_json,
                   created_at, updated_at
            FROM pull_requests WHERE id = ?
            """,
            (pr_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return PRStatusResponse(
            pr_id=row["id"],
            workspace_id=row["workspace_id"],
            repo_full_name=row["repo_full_name"],
            pr_number=row["pr_number"],
            pr_url=row["pr_url"],
            head_branch=row["head_branch"],
            status=row["status"],
            ci_status=row["ci_status"],
            merged_at=row["merged_at"],
            gatekeeper=json.loads(row["gatekeeper_verdict_json"]) if row["gatekeeper_verdict_json"] else None,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def get_by_repo_and_number(self, repo_full_name: str, pr_number: int) -> Optional[tuple[PRStatusResponse, int]]:
        """Returns (PRStatusResponse, user_id)"""
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT id, workspace_id, user_id, repo_full_name, pr_number, pr_url,
                   head_branch, status, ci_status, merged_at, gatekeeper_verdict_json,
                   created_at, updated_at
            FROM pull_requests
            WHERE LOWER(repo_full_name) = LOWER(?) AND pr_number = ?
            """,
            (repo_full_name, pr_number),
        )
        row = cur.fetchone()
        if not row:
            return None
        resp = PRStatusResponse(
            pr_id=row["id"],
            workspace_id=row["workspace_id"],
            repo_full_name=row["repo_full_name"],
            pr_number=row["pr_number"],
            pr_url=row["pr_url"],
            head_branch=row["head_branch"],
            status=row["status"],
            ci_status=row["ci_status"],
            merged_at=row["merged_at"],
            gatekeeper=json.loads(row["gatekeeper_verdict_json"]) if row["gatekeeper_verdict_json"] else None,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
        return resp, row["user_id"]

    def update_status(
        self,
        pr_id: str,
        status: str,
        ci_status: Optional[str] = None,
        merged: bool = False,
    ) -> None:
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        cur = self.conn.cursor()
        merged_val = now if merged else None
        if ci_status is not None:
            cur.execute(
                """
                UPDATE pull_requests
                SET status = ?, ci_status = ?, merged_at = COALESCE(?, merged_at), updated_at = ?
                WHERE id = ?
                """,
                (status, ci_status, merged_val, now, pr_id),
            )
        else:
            cur.execute(
                """
                UPDATE pull_requests
                SET status = ?, merged_at = COALESCE(?, merged_at), updated_at = ?
                WHERE id = ?
                """,
                (status, merged_val, now, pr_id),
            )

    def list_by_user(self, user_id: int) -> List[PRStatusResponse]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT id, workspace_id, user_id, repo_full_name, pr_number, pr_url,
                   head_branch, status, ci_status, merged_at, gatekeeper_verdict_json,
                   created_at, updated_at
            FROM pull_requests
            WHERE user_id = ?
            ORDER BY created_at DESC
            """,
            (user_id,),
        )
        results = []
        for row in cur.fetchall():
            results.append(
                PRStatusResponse(
                    pr_id=row["id"],
                    workspace_id=row["workspace_id"],
                    repo_full_name=row["repo_full_name"],
                    pr_number=row["pr_number"],
                    pr_url=row["pr_url"],
                    head_branch=row["head_branch"],
                    status=row["status"],
                    ci_status=row["ci_status"],
                    merged_at=row["merged_at"],
                    gatekeeper=json.loads(row["gatekeeper_verdict_json"]) if row["gatekeeper_verdict_json"] else None,
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
            )
        return results
