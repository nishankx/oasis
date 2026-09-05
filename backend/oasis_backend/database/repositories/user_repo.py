"""
User database repository.
"""

from __future__ import annotations
import datetime
import sqlite3
from typing import Optional
from oasis_backend.models.auth import GitHubUserPayload, UserRecord


class UserRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def get_by_id(self, user_id: int) -> Optional[UserRecord]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT id, github_id, username, name, email, avatar_url, created_at, updated_at
            FROM users WHERE id = ?
            """,
            (user_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return UserRecord(
            id=row["id"],
            github_id=row["github_id"],
            username=row["username"],
            name=row["name"],
            email=row["email"],
            avatar_url=row["avatar_url"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def get_by_github_id(self, github_id: int) -> Optional[UserRecord]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT id, github_id, username, name, email, avatar_url, created_at, updated_at
            FROM users WHERE github_id = ?
            """,
            (github_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return UserRecord(
            id=row["id"],
            github_id=row["github_id"],
            username=row["username"],
            name=row["name"],
            email=row["email"],
            avatar_url=row["avatar_url"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def get_by_username(self, username: str) -> Optional[UserRecord]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT id, github_id, username, name, email, avatar_url, created_at, updated_at
            FROM users WHERE LOWER(username) = LOWER(?)
            """,
            (username,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return UserRecord(
            id=row["id"],
            github_id=row["github_id"],
            username=row["username"],
            name=row["name"],
            email=row["email"],
            avatar_url=row["avatar_url"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def get_encrypted_token(self, user_id: int) -> Optional[str]:
        cur = self.conn.cursor()
        cur.execute("SELECT encrypted_access_token FROM users WHERE id = ?", (user_id,))
        row = cur.fetchone()
        return row["encrypted_access_token"] if row else None

    def upsert_user(
        self,
        gh_user: GitHubUserPayload,
        encrypted_token: str,
    ) -> UserRecord:
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO users (github_id, username, name, email, avatar_url, encrypted_access_token, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(github_id) DO UPDATE SET
                username = excluded.username,
                name = excluded.name,
                email = excluded.email,
                avatar_url = excluded.avatar_url,
                encrypted_access_token = excluded.encrypted_access_token,
                updated_at = excluded.updated_at
            RETURNING id, github_id, username, name, email, avatar_url, created_at, updated_at
            """,
            (
                gh_user.id,
                gh_user.login,
                gh_user.name,
                gh_user.email,
                gh_user.avatar_url,
                encrypted_token,
                now,
                now,
            ),
        )
        row = cur.fetchone()
        return UserRecord(
            id=row["id"],
            github_id=row["github_id"],
            username=row["username"],
            name=row["name"],
            email=row["email"],
            avatar_url=row["avatar_url"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
