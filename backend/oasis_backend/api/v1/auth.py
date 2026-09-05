"""
Authentication router: GitHub OAuth and JWT session management.
"""

from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from oasis_backend.api.deps import get_auth_service, get_current_user, get_optional_user, get_profile_service
from oasis_backend.models.auth import (
    AuthCallbackRequest,
    AuthSessionResponse,
    GitHubAuthUrlResponse,
    UserRecord,
)
from oasis_backend.services.auth_service import AuthService
from oasis_backend.services.profile_service import ProfileService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/github/url", response_model=GitHubAuthUrlResponse)
def get_github_auth_url(
    redirect_uri: Optional[str] = Query(None, description="Optional custom OAuth callback URI"),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Returns the GitHub OAuth login URL with required scopes."""
    try:
        return auth_service.generate_oauth_url(redirect_uri)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )


@router.get("/github/login")
def get_github_login_redirect(
    redirect_uri: Optional[str] = Query(None, description="Optional custom OAuth callback URI"),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Directly redirects browser to GitHub OAuth authorization URL."""
    try:
        auth_resp = auth_service.generate_oauth_url(redirect_uri)
        return RedirectResponse(url=auth_resp.url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )


@router.post("/github/callback", response_model=AuthSessionResponse)
async def github_oauth_callback(
    req: AuthCallbackRequest,
    auth_service: AuthService = Depends(get_auth_service),
    profile_service: ProfileService = Depends(get_profile_service),
):
    """
    Exchanges GitHub OAuth code for access token, stores user, initiates initial profile analysis,
    and returns a JWT session token.
    """
    try:
        user, jwt_token = await auth_service.authenticate_github_code(req.code, redirect_uri=req.redirect_uri)

        # Trigger initial background profile build
        token = auth_service.get_decrypted_user_token(user.id)
        try:
            await profile_service.build_or_refresh_profile(user.id, user.username, token)
        except Exception:
            pass  # Non-fatal during login

        return AuthSessionResponse(
            authenticated=True,
            user=user,
            token=jwt_token,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"GitHub authentication failed: {e}",
        )


@router.get("/session", response_model=AuthSessionResponse)
def get_current_session(
    current_user: Optional[UserRecord] = Depends(get_optional_user),
):
    """Validates session token and returns logged-in user details."""
    if not current_user:
        return AuthSessionResponse(authenticated=False, user=None, token=None)
    return AuthSessionResponse(authenticated=True, user=current_user, token=None)


@router.post("/logout")
def logout():
    """Client logout confirmation."""
    return {"message": "Logged out successfully."}
