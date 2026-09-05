"""
Contribution scoring and leaderboard models.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ScoreBreakdown(BaseModel):
    base_score: int = 100
    confidence_bonus: int = 0
    diff_bonus: int = 0
    repo_bonus: int = 0
    total_score: int = 100
    explanation: str


class ContributionRecord(BaseModel):
    id: str
    user_id: int
    pr_id: str
    repo_full_name: str
    pr_number: int
    pr_url: str
    base_score: int
    confidence_bonus: int
    diff_bonus: int
    repo_bonus: int
    total_score: int
    breakdown: ScoreBreakdown
    awarded_at: str


class LeaderboardEntry(BaseModel):
    rank: int
    user_id: int
    username: str
    avatar_url: Optional[str] = None
    cumulative_score: int
    rank_tier: str
    total_contributions: int
