"""
Scoring service: transparent, explainable contribution point evaluation and leaderboard engine.
"""

from __future__ import annotations
import math
import uuid
from typing import Any, Dict, List, Optional
from oasis_backend.database.repositories.scoring_repo import ScoringRepository
from oasis_backend.models.scoring import ContributionRecord, LeaderboardEntry, ScoreBreakdown


class ScoringService:
    def __init__(self, scoring_repo: ScoringRepository):
        self.scoring_repo = scoring_repo

    def calculate_score(
        self,
        gatekeeper_confidence: float = 0.85,
        insertions: int = 15,
        deletions: int = 5,
        repo_stars: int = 100,
    ) -> tuple[int, int, int, int, int, ScoreBreakdown]:
        """
        Calculates explainable contribution points:
        - Base: 100 points
        - Confidence bonus: round(confidence * 50) [0 - 50]
        - Diff complexity bonus: min(50, round(ln(insertions + deletions + 1) * 10)) [0 - 50]
        - Repo prestige bonus: min(50, round(log10(stars + 1) * 12)) [0 - 50]
        """
        base_score = 100

        # Gatekeeper confidence bonus (0 - 50)
        confidence_bonus = max(0, min(50, round(gatekeeper_confidence * 50)))

        # Diff complexity bonus (0 - 50)
        total_diff_lines = max(0, insertions + deletions)
        diff_bonus = min(50, round(math.log(total_diff_lines + 1) * 10))

        # Repo prestige bonus (0 - 50)
        repo_bonus = min(50, round(math.log10(max(0, repo_stars) + 1) * 12))

        total_score = base_score + confidence_bonus + diff_bonus + repo_bonus

        explanation = (
            f"Base Merged PR (+{base_score}) + "
            f"Gatekeeper Confidence {int(gatekeeper_confidence * 100)}% (+{confidence_bonus}) + "
            f"Patch Scope {total_diff_lines} lines (+{diff_bonus}) + "
            f"Target Repo Health (+{repo_bonus})"
        )

        breakdown = ScoreBreakdown(
            base_score=base_score,
            confidence_bonus=confidence_bonus,
            diff_bonus=diff_bonus,
            repo_bonus=repo_bonus,
            total_score=total_score,
            explanation=explanation,
        )

        return base_score, confidence_bonus, diff_bonus, repo_bonus, total_score, breakdown

    def award_merged_pr(
        self,
        user_id: int,
        pr_id: str,
        gatekeeper_confidence: float = 0.85,
        insertions: int = 10,
        deletions: int = 2,
        repo_stars: int = 50,
    ) -> ContributionRecord:
        """Awards contribution score for a merged PR if not already awarded."""
        existing = self.scoring_repo.get_by_pr_id(pr_id)
        if existing:
            return existing

        base, conf_b, diff_b, repo_b, total, breakdown = self.calculate_score(
            gatekeeper_confidence=gatekeeper_confidence,
            insertions=insertions,
            deletions=deletions,
            repo_stars=repo_stars,
        )

        contribution_id = f"cnt_{uuid.uuid4().hex[:12]}"
        return self.scoring_repo.create_contribution(
            contribution_id=contribution_id,
            user_id=user_id,
            pr_id=pr_id,
            base_score=base,
            confidence_bonus=conf_b,
            diff_bonus=diff_b,
            repo_bonus=repo_b,
            total_score=total,
            breakdown=breakdown,
        )

    def get_user_contributions(self, user_id: int) -> List[ContributionRecord]:
        return self.scoring_repo.list_by_user(user_id)

    def get_leaderboard(self, limit: int = 50) -> List[LeaderboardEntry]:
        return self.scoring_repo.get_leaderboard(limit)
