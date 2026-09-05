"""
Workspace API router: Monaco editor backend, ephemeral file sandbox, and diff management.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from oasis_backend.api.deps import (
    get_auth_service,
    get_current_user,
    get_workspace_repo,
    get_workspace_service,
)
from oasis_backend.database.repositories.workspace_repo import WorkspaceRepository
from oasis_backend.models.auth import UserRecord
from oasis_backend.models.workspace import (
    FileContentResponse,
    FileNode,
    SaveFileRequest,
    SaveFileResponse,
    WorkspaceCreateRequest,
    WorkspaceDiffResponse,
    WorkspaceSession,
)
from oasis_backend.services.auth_service import AuthService
from oasis_backend.services.workspace_service import WorkspaceService

router = APIRouter(prefix="/workspace", tags=["Workspace"])


@router.post("/prepare", response_model=WorkspaceSession, status_code=status.HTTP_201_CREATED)
def prepare_workspace(
    req: WorkspaceCreateRequest,
    current_user: UserRecord = Depends(get_current_user),
    workspace_service: WorkspaceService = Depends(get_workspace_service),
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Initializes an isolated ephemeral workspace for a recommended repo + issue,
    checks out issue branch, extracts relevant files via oasis-agent, and returns session.
    """
    token = auth_service.get_decrypted_user_token(current_user.id)
    try:
        return workspace_service.prepare_workspace(
            user_id=current_user.id,
            repo_url=req.repo_url,
            issue_number=req.issue_number,
            github_token=token,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to prepare workspace: {e}",
        )


@router.get("", response_model=List[WorkspaceSession])
def list_user_workspaces(
    current_user: UserRecord = Depends(get_current_user),
    workspace_repo: WorkspaceRepository = Depends(get_workspace_repo),
):
    """Lists all active workspaces for the authenticated user."""
    return workspace_repo.list_by_user(current_user.id)


@router.get("/{workspace_id}", response_model=WorkspaceSession)
def get_workspace_session(
    workspace_id: str,
    current_user: UserRecord = Depends(get_current_user),
    workspace_service: WorkspaceService = Depends(get_workspace_service),
):
    """Retrieves session metadata for a workspace."""
    try:
        session, _ = workspace_service.get_workspace_or_404(workspace_id, current_user.id)
        return session
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found.")
    except PermissionError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")


@router.get("/{workspace_id}/tree", response_model=List[FileNode])
def get_workspace_file_tree(
    workspace_id: str,
    current_user: UserRecord = Depends(get_current_user),
    workspace_service: WorkspaceService = Depends(get_workspace_service),
):
    """Returns the workspace file tree for Monaco editor navigation."""
    try:
        return workspace_service.build_file_tree(workspace_id, current_user.id)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found.")
    except PermissionError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")


@router.get("/{workspace_id}/file", response_model=FileContentResponse)
def read_workspace_file(
    workspace_id: str,
    path: str = Query(..., description="Relative file path inside workspace"),
    current_user: UserRecord = Depends(get_current_user),
    workspace_service: WorkspaceService = Depends(get_workspace_service),
):
    """Reads file content from workspace for Monaco editor rendering."""
    try:
        return workspace_service.read_file(workspace_id, path, current_user.id)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found.")
    except PermissionError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"File '{path}' not found.")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/{workspace_id}/file", response_model=SaveFileResponse)
def save_workspace_file(
    workspace_id: str,
    req: SaveFileRequest,
    current_user: UserRecord = Depends(get_current_user),
    workspace_service: WorkspaceService = Depends(get_workspace_service),
):
    """Saves edited content to a file in the workspace (staged locally, not committed yet)."""
    try:
        return workspace_service.write_file(workspace_id, req.path, req.content, current_user.id)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found.")
    except PermissionError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{workspace_id}/diff", response_model=WorkspaceDiffResponse)
def get_workspace_diff(
    workspace_id: str,
    current_user: UserRecord = Depends(get_current_user),
    workspace_service: WorkspaceService = Depends(get_workspace_service),
):
    """Returns the git diff of changes made in the workspace against the base branch."""
    try:
        return workspace_service.get_diff(workspace_id, current_user.id)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found.")
    except PermissionError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")


@router.post("/{workspace_id}/ai-fix")
def generate_ai_fix(
    workspace_id: str,
    instruction: Optional[str] = Query(None, description="Optional custom instruction"),
    current_user: UserRecord = Depends(get_current_user),
    workspace_service: WorkspaceService = Depends(get_workspace_service),
):
    """Asks oasis-agent to propose a fix patch for the workspace issue."""
    try:
        return workspace_service.apply_ai_fix(workspace_id, instruction, current_user.id)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found.")
    except PermissionError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")


@router.delete("/{workspace_id}")
def delete_workspace(
    workspace_id: str,
    current_user: UserRecord = Depends(get_current_user),
    workspace_service: WorkspaceService = Depends(get_workspace_service),
):
    """Cleans up and removes an ephemeral workspace."""
    try:
        workspace_service.get_workspace_or_404(workspace_id, current_user.id)
        workspace_service.cleanup_workspace(workspace_id)
        return {"message": f"Workspace '{workspace_id}' successfully cleaned up."}
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found.")
    except PermissionError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
