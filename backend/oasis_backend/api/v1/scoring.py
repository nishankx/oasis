"""
Scoring API router: contribution points, breakdown explanations, and leaderboard.
"""

from __future__ import annotations
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from oasis_backend.api.deps import (
    get_current_user,
    get_scoring_repo,
    get_scoring_service,
    get_user_repo,
)
from oasis_backend.database.repositories.scoring_repo import ScoringRepository
from oasis_backend.database.repositories.user_repo import UserRepository
from oasis_backend.models.auth import UserRecord
from oasis_backend.models.scoring import ContributionRecord, LeaderboardEntry
from oasis_backend.services.scoring_service import ScoringService

router = APIRouter(prefix="/scoring", tags=["Scoring & Leaderboard"])


@router.get("/leaderboard", response_model=List[LeaderboardEntry])
def get_leaderboard(
    limit: int = Query(50, ge=1, le=100),
    scoring_service: ScoringService = Depends(get_scoring_service),
):
    """Returns top ranked contributors sorted by verified contribution points."""
    return scoring_service.get_leaderboard(limit)


@router.get("/contributions/me", response_model=List[ContributionRecord])
def get_my_contributions(
    current_user: UserRecord = Depends(get_current_user),
    scoring_service: ScoringService = Depends(get_scoring_service),
):
    """Returns all verified contributions and score breakdowns for the current user."""
    return scoring_service.get_user_contributions(current_user.id)


@router.get("/contributions/{username}", response_model=List[ContributionRecord])
def get_user_contributions(
    username: str,
    user_repo: UserRepository = Depends(get_user_repo),
    scoring_repo: ScoringRepository = Depends(get_scoring_repo),
):
    """Returns contribution history for a public profile."""
    user = user_repo.get_by_username(username)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User '{username}' not found.")
    return scoring_repo.list_by_user(user.id)
