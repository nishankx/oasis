"""
Discovery API router: repository and issue recommendation endpoints.
"""

from __future__ import annotations
from fastapi import APIRouter, Depends, Query
from oasis_backend.api.deps import (
    get_auth_service,
    get_current_user,
    get_discovery_service,
    get_profile_service,
)
from oasis_backend.models.auth import UserRecord
from oasis_backend.models.discovery import DiscoveryResponse
from oasis_backend.services.auth_service import AuthService
from oasis_backend.services.discovery_service import DiscoveryService
from oasis_backend.services.profile_service import ProfileService

router = APIRouter(prefix="/discovery", tags=["Discovery"])


@router.get("/repos", response_model=DiscoveryResponse)
async def get_recommended_repos(
    limit: int = Query(20, ge=1, le=50, description="Max candidate repos to return"),
    current_user: UserRecord = Depends(get_current_user),
    discovery_service: DiscoveryService = Depends(get_discovery_service),
    profile_service: ProfileService = Depends(get_profile_service),
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Fetches personalized repository recommendations based on the user's expertise profile
    and open issues with 'good first issue' or 'help wanted' labels.
    """
    profile = profile_service.get_profile(current_user.id)
    token = auth_service.get_decrypted_user_token(current_user.id)
    if not profile:
        profile = await profile_service.build_or_refresh_profile(
            current_user.id, current_user.username, token
        )

    return await discovery_service.get_recommended_repos(
        user_id=current_user.id,
        expertise=profile.expertise,
        github_token=token,
        limit=limit,
        force_refresh=False,
    )


@router.post("/refresh", response_model=DiscoveryResponse)
async def refresh_discovery_cache(
    limit: int = Query(20, ge=1, le=50),
    current_user: UserRecord = Depends(get_current_user),
    discovery_service: DiscoveryService = Depends(get_discovery_service),
    profile_service: ProfileService = Depends(get_profile_service),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Forces cache invalidation and re-queries GitHub Search API for candidate repositories."""
    profile = profile_service.get_profile(current_user.id)
    token = auth_service.get_decrypted_user_token(current_user.id)
    if not profile:
        profile = await profile_service.build_or_refresh_profile(
            current_user.id, current_user.username, token
        )

    return await discovery_service.get_recommended_repos(
        user_id=current_user.id,
        expertise=profile.expertise,
        github_token=token,
        limit=limit,
        force_refresh=True,
    )


@router.get("/search", response_model=DiscoveryResponse)
async def search_repositories(
    q: str = Query(..., min_length=1, description="Repository query, e.g. 'owner/repo' or search terms"),
    limit: int = Query(15, ge=1, le=50),
    current_user: UserRecord = Depends(get_current_user),
    discovery_service: DiscoveryService = Depends(get_discovery_service),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Searches GitHub repositories directly by keyword, language, or exact 'owner/repo'."""
    token = auth_service.get_decrypted_user_token(current_user.id)
    candidates = await discovery_service.search_repos(
        query=q,
        github_token=token,
        limit=limit,
    )
    return DiscoveryResponse(
        repos=candidates,
        total=len(candidates),
        cached=False,
    )
