"""
PR API router: pre-push Gatekeeper validation, PR opening, and status tracking.
"""

from __future__ import annotations
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from oasis_backend.api.deps import (
    get_auth_service,
    get_current_user,
    get_pr_repo,
    get_pr_service,
)
from oasis_backend.database.repositories.pr_repo import PullRequestRepository
from oasis_backend.models.auth import UserRecord
from oasis_backend.models.pr import PRStatusResponse, PushPRRequest, PushPRResponse
from oasis_backend.services.auth_service import AuthService
from oasis_backend.services.pr_service import PRService

router = APIRouter(prefix="/pr", tags=["Pull Requests"])


@router.post("/push", response_model=PushPRResponse)
async def push_and_open_pr(
    req: PushPRRequest,
    current_user: UserRecord = Depends(get_current_user),
    pr_service: PRService = Depends(get_pr_service),
):
    """
    Evaluates workspace diff through the meaningfulness gatekeeper.
    If approved: pushes the branch and opens a PR on GitHub under the authenticated user's account.
    If rejected: halts and returns gatekeeper reasoning.
    """
    try:
        return await pr_service.evaluate_and_push(
            user_id=current_user.id,
            workspace_id=req.workspace_id,
            custom_commit_message=req.custom_commit_message,
            dry_run=req.dry_run,
            force=req.force,
        )
    except PermissionError as pe:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(pe))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PR push process failed: {e}",
        )


@router.get("/{pr_id}/status", response_model=PRStatusResponse)
async def get_pr_status(
    pr_id: str,
    current_user: UserRecord = Depends(get_current_user),
    pr_repo: PullRequestRepository = Depends(get_pr_repo),
    pr_service: PRService = Depends(get_pr_service),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Retrieves current PR status and checks for updates (polling fallback)."""
    pr = pr_repo.get_by_id(pr_id)
    if not pr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"PR '{pr_id}' not found.")

    token = auth_service.get_decrypted_user_token(current_user.id)
    updated_pr = await pr_service.poll_pr_status(pr_id, github_token=token)
    return updated_pr or pr


@router.get("", response_model=List[PRStatusResponse])
def list_user_prs(
    current_user: UserRecord = Depends(get_current_user),
    pr_repo: PullRequestRepository = Depends(get_pr_repo),
):
    """Lists all pull requests opened by the authenticated user."""
    return pr_repo.list_by_user(current_user.id)
