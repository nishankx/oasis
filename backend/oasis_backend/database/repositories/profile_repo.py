"""
Profile and snapshot database repository.
"""

from __future__ import annotations
import datetime
import json
import sqlite3
from typing import List, Optional
from oasis_backend.models.profile import ExpertiseVector, ProfileRecord, ProfileSnapshotRecord


class ProfileRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def get_profile(self, user_id: int) -> Optional[ProfileRecord]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT user_id, languages_json, topics_json, activity_level, cumulative_score, rank_tier, last_computed
            FROM profiles WHERE user_id = ?
            """,
            (user_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        expertise = ExpertiseVector(
            languages=json.loads(row["languages_json"] or "{}"),
            topics=json.loads(row["topics_json"] or "{}"),
            activity_level=row["activity_level"] or "medium",
            last_computed=row["last_computed"],
        )
        return ProfileRecord(
            user_id=row["user_id"],
            expertise=expertise,
            cumulative_score=row["cumulative_score"],
            rank_tier=row["rank_tier"],
        )

    def upsert_profile(
        self,
        user_id: int,
        expertise: ExpertiseVector,
        cumulative_score: Optional[int] = None,
        rank_tier: Optional[str] = None,
    ) -> ProfileRecord:
        cur = self.conn.cursor()
        existing = self.get_profile(user_id)

        final_score = cumulative_score if cumulative_score is not None else (existing.cumulative_score if existing else 0)
        final_tier = rank_tier if rank_tier is not None else (existing.rank_tier if existing else "Novice Contributor")

        cur.execute(
            """
            INSERT INTO profiles (user_id, languages_json, topics_json, activity_level, cumulative_score, rank_tier, last_computed)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                languages_json = excluded.languages_json,
                topics_json = excluded.topics_json,
                activity_level = excluded.activity_level,
                cumulative_score = excluded.cumulative_score,
                rank_tier = excluded.rank_tier,
                last_computed = excluded.last_computed
            """,
            (
                user_id,
                json.dumps(expertise.languages),
                json.dumps(expertise.topics),
                expertise.activity_level,
                final_score,
                final_tier,
                expertise.last_computed,
            ),
        )

        # Also store versioned snapshot
        cur.execute(
            """
            INSERT INTO profile_snapshots (user_id, languages_json, topics_json, activity_level, cumulative_score, snapshot_timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                json.dumps(expertise.languages),
                json.dumps(expertise.topics),
                expertise.activity_level,
                final_score,
                expertise.last_computed,
            ),
        )

        return ProfileRecord(
            user_id=user_id,
            expertise=expertise,
            cumulative_score=final_score,
            rank_tier=final_tier,
        )

    def get_snapshots(self, user_id: int, limit: int = 10) -> List[ProfileSnapshotRecord]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT id, user_id, languages_json, topics_json, activity_level, cumulative_score, snapshot_timestamp
            FROM profile_snapshots
            WHERE user_id = ?
            ORDER BY snapshot_timestamp DESC
            LIMIT ?
            """,
            (user_id, limit),
        )
        records = []
        for row in cur.fetchall():
            records.append(
                ProfileSnapshotRecord(
                    id=row["id"],
                    user_id=row["user_id"],
                    expertise=ExpertiseVector(
                        languages=json.loads(row["languages_json"]),
                        topics=json.loads(row["topics_json"]),
                        activity_level=row["activity_level"],
                        last_computed=row["snapshot_timestamp"],
                    ),
                    cumulative_score=row["cumulative_score"],
                    snapshot_timestamp=row["snapshot_timestamp"],
                )
            )
        return records
