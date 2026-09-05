"""
Profile API router: expertise graphs, refresh, and public user profiles.
"""

from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from oasis_backend.api.deps import (
    get_auth_service,
    get_current_user,
    get_profile_repo,
    get_profile_service,
    get_scoring_repo,
    get_user_repo,
)
from oasis_backend.database.repositories.profile_repo import ProfileRepository
from oasis_backend.database.repositories.scoring_repo import ScoringRepository
from oasis_backend.database.repositories.user_repo import UserRepository
from oasis_backend.models.auth import UserRecord
from oasis_backend.models.profile import ExpertiseVector, ProfileRecord, PublicUserProfile
from oasis_backend.services.auth_service import AuthService
from oasis_backend.services.profile_service import ProfileService

router = APIRouter(prefix="/profile", tags=["Profile"])


@router.get("/me", response_model=ProfileRecord)
async def get_my_profile(
    current_user: UserRecord = Depends(get_current_user),
    profile_service: ProfileService = Depends(get_profile_service),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Returns the authenticated developer's expertise graph and profile."""
    profile = profile_service.get_profile(current_user.id)
    if not profile:
        # Generate on the fly
        token = auth_service.get_decrypted_user_token(current_user.id)
        profile = await profile_service.build_or_refresh_profile(
            current_user.id, current_user.username, token
        )
    return profile


@router.post("/refresh", response_model=ProfileRecord)
async def refresh_my_profile(
    current_user: UserRecord = Depends(get_current_user),
    profile_service: ProfileService = Depends(get_profile_service),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Re-analyzes GitHub repositories, stars, events, and pinned items."""
    token = auth_service.get_decrypted_user_token(current_user.id)
    return await profile_service.build_or_refresh_profile(
        current_user.id, current_user.username, token
    )


@router.get("/{username}", response_model=PublicUserProfile)
def get_public_profile(
    username: str,
    user_repo: UserRepository = Depends(get_user_repo),
    profile_repo: ProfileRepository = Depends(get_profile_repo),
    scoring_repo: ScoringRepository = Depends(get_scoring_repo),
):
    """Returns a public user profile, score, and contribution stats."""
    user = user_repo.get_by_username(username)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User '{username}' not found.")

    profile = profile_repo.get_profile(user.id)
    contributions = scoring_repo.list_by_user(user.id)

    expertise = profile.expertise if profile else ExpertiseVector(
        languages={}, topics={}, activity_level="medium", last_computed=user.created_at
    )
    score = profile.cumulative_score if profile else 0
    rank = profile.rank_tier if profile else "Novice Contributor"

    return PublicUserProfile(
        username=user.username,
        name=user.name,
        avatar_url=user.avatar_url,
        cumulative_score=score,
        rank_tier=rank,
        expertise=expertise,
        recent_contributions_count=len(contributions),
    )
