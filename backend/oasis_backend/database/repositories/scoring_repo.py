"""
Contribution scoring and leaderboard database repository.
"""

from __future__ import annotations
import datetime
import json
import sqlite3
from typing import List, Optional
from oasis_backend.models.scoring import ContributionRecord, LeaderboardEntry, ScoreBreakdown


class ScoringRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def create_contribution(
        self,
        contribution_id: str,
        user_id: int,
        pr_id: str,
        base_score: int,
        confidence_bonus: int,
        diff_bonus: int,
        repo_bonus: int,
        total_score: int,
        breakdown: ScoreBreakdown,
    ) -> ContributionRecord:
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO contributions (
                id, user_id, pr_id, base_score, confidence_bonus,
                diff_bonus, repo_bonus, total_score, breakdown_json, awarded_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                contribution_id,
                user_id,
                pr_id,
                base_score,
                confidence_bonus,
                diff_bonus,
                repo_bonus,
                total_score,
                breakdown.model_dump_json(),
                now,
            ),
        )

        # Update cumulative score on profile
        cur.execute(
            """
            UPDATE profiles
            SET cumulative_score = cumulative_score + ?
            WHERE user_id = ?
            """,
            (total_score, user_id),
        )

        # Calculate rank tier based on new total score
        cur.execute("SELECT cumulative_score FROM profiles WHERE user_id = ?", (user_id,))
        p_row = cur.fetchone()
        new_score = p_row["cumulative_score"] if p_row else total_score
        new_tier = self.derive_rank_tier(new_score)
        cur.execute("UPDATE profiles SET rank_tier = ? WHERE user_id = ?", (new_tier, user_id))

        # Fetch PR details for response
        cur.execute("SELECT repo_full_name, pr_number, pr_url FROM pull_requests WHERE id = ?", (pr_id,))
        pr_row = cur.fetchone()

        return ContributionRecord(
            id=contribution_id,
            user_id=user_id,
            pr_id=pr_id,
            repo_full_name=pr_row["repo_full_name"] if pr_row else "unknown",
            pr_number=pr_row["pr_number"] if pr_row else 0,
            pr_url=pr_row["pr_url"] if pr_row else "",
            base_score=base_score,
            confidence_bonus=confidence_bonus,
            diff_bonus=diff_bonus,
            repo_bonus=repo_bonus,
            total_score=total_score,
            breakdown=breakdown,
            awarded_at=now,
        )

    def get_by_pr_id(self, pr_id: str) -> Optional[ContributionRecord]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT c.id, c.user_id, c.pr_id, c.base_score, c.confidence_bonus,
                   c.diff_bonus, c.repo_bonus, c.total_score, c.breakdown_json, c.awarded_at,
                   pr.repo_full_name, pr.pr_number, pr.pr_url
            FROM contributions c
            JOIN pull_requests pr ON pr.id = c.pr_id
            WHERE c.pr_id = ?
            """,
            (pr_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return ContributionRecord(
            id=row["id"],
            user_id=row["user_id"],
            pr_id=row["pr_id"],
            repo_full_name=row["repo_full_name"],
            pr_number=row["pr_number"],
            pr_url=row["pr_url"],
            base_score=row["base_score"],
            confidence_bonus=row["confidence_bonus"],
            diff_bonus=row["diff_bonus"],
            repo_bonus=row["repo_bonus"],
            total_score=row["total_score"],
            breakdown=ScoreBreakdown.model_validate_json(row["breakdown_json"]),
            awarded_at=row["awarded_at"],
        )

    def list_by_user(self, user_id: int) -> List[ContributionRecord]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT c.id, c.user_id, c.pr_id, c.base_score, c.confidence_bonus,
                   c.diff_bonus, c.repo_bonus, c.total_score, c.breakdown_json, c.awarded_at,
                   pr.repo_full_name, pr.pr_number, pr.pr_url
            FROM contributions c
            JOIN pull_requests pr ON pr.id = c.pr_id
            WHERE c.user_id = ?
            ORDER BY c.awarded_at DESC
            """,
            (user_id,),
        )
        results = []
        for row in cur.fetchall():
            results.append(
                ContributionRecord(
                    id=row["id"],
                    user_id=row["user_id"],
                    pr_id=row["pr_id"],
                    repo_full_name=row["repo_full_name"],
                    pr_number=row["pr_number"],
                    pr_url=row["pr_url"],
                    base_score=row["base_score"],
                    confidence_bonus=row["confidence_bonus"],
                    diff_bonus=row["diff_bonus"],
                    repo_bonus=row["repo_bonus"],
                    total_score=row["total_score"],
                    breakdown=ScoreBreakdown.model_validate_json(row["breakdown_json"]),
                    awarded_at=row["awarded_at"],
                )
            )
        return results

    def get_leaderboard(self, limit: int = 50) -> List[LeaderboardEntry]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT u.id as user_id, u.username, u.avatar_url,
                   COALESCE(p.cumulative_score, 0) as score,
                   COALESCE(p.rank_tier, 'Novice Contributor') as rank_tier,
                   COUNT(c.id) as total_contributions
            FROM users u
            LEFT JOIN profiles p ON p.user_id = u.id
            LEFT JOIN contributions c ON c.user_id = u.id
            GROUP BY u.id
            ORDER BY score DESC, total_contributions DESC
            LIMIT ?
            """,
            (limit,),
        )
        results = []
        for idx, row in enumerate(cur.fetchall(), 1):
            results.append(
                LeaderboardEntry(
                    rank=idx,
                    user_id=row["user_id"],
                    username=row["username"],
                    avatar_url=row["avatar_url"],
                    cumulative_score=row["score"],
                    rank_tier=row["rank_tier"],
                    total_contributions=row["total_contributions"],
                )
            )
        return results

    @staticmethod
    def derive_rank_tier(score: int) -> str:
        if score >= 2000:
            return "Legendary Maintainer"
        if score >= 1000:
            return "Core Architect"
        if score >= 500:
            return "Senior Contributor"
        if score >= 200:
            return "Active Contributor"
        return "Novice Contributor"
