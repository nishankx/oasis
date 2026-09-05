"""
Discovery recommendation cache repository.
"""

from __future__ import annotations
import datetime
import json
import sqlite3
from typing import List, Optional
from oasis_backend.models.discovery import CandidateRepo, DiscoveryResponse


class DiscoveryRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def get_cached(self, user_id: int) -> Optional[DiscoveryResponse]:
        cur = self.conn.cursor()
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        cur.execute(
            """
            SELECT repos_json, cached_at, expires_at
            FROM discovery_cache
            WHERE user_id = ? AND expires_at > ?
            """,
            (user_id, now),
        )
        row = cur.fetchone()
        if not row:
            return None

        data = json.loads(row["repos_json"])
        repos = [CandidateRepo.model_validate(r) for r in data]
        return DiscoveryResponse(
            repos=repos,
            total=len(repos),
            cached=True,
            cached_at=row["cached_at"],
            expires_at=row["expires_at"],
        )

    def set_cache(self, user_id: int, repos: List[CandidateRepo], ttl_hours: int = 6) -> None:
        now_dt = datetime.datetime.now(datetime.timezone.utc)
        now = now_dt.isoformat()
        expires = (now_dt + datetime.timedelta(hours=ttl_hours)).isoformat()
        repos_json = json.dumps([r.model_dump() for r in repos])

        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO discovery_cache (user_id, repos_json, cached_at, expires_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                repos_json = excluded.repos_json,
                cached_at = excluded.cached_at,
                expires_at = excluded.expires_at
            """,
            (user_id, repos_json, now, expires),
        )

    def invalidate(self, user_id: int) -> None:
        cur = self.conn.cursor()
        cur.execute("DELETE FROM discovery_cache WHERE user_id = ?", (user_id,))
