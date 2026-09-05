"""
Agent API router: exposes oasis-agent library core functions as an internal service.
"""

from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status
from oasis_agent.git_ops.client import GitClient
from oasis_agent.models import GitDiffSummary, IssueContext
from oasis_backend.api.deps import get_agent_gateway, get_current_user, get_workspace_service
from oasis_backend.models.agent import (
    AgentContextRequest,
    AgentContextResponse,
    AgentEvaluateRequest,
    AgentSuggestFixRequest,
    AgentSuggestFixResponse,
    GatekeeperVerdictResponse,
)
from oasis_backend.models.auth import UserRecord
from oasis_backend.services.agent_gateway import AgentGatewayService
from oasis_backend.services.workspace_service import WorkspaceService

router = APIRouter(prefix="/agent", tags=["Agent Gateway"])


@router.post("/context", response_model=AgentContextResponse)
def get_agent_context(
    req: AgentContextRequest,
    current_user: UserRecord = Depends(get_current_user),
    workspace_service: WorkspaceService = Depends(get_workspace_service),
    agent_gateway: AgentGatewayService = Depends(get_agent_gateway),
):
    """Builds codebase context and extracts relevant files for the workspace issue."""
    session, local_path = workspace_service.get_workspace_or_404(req.workspace_id, current_user.id)
    issue_file = local_path / ".oasis-agent" / "issue.json"
    if issue_file.exists():
        issue_ctx = IssueContext.model_validate_json(issue_file.read_text(encoding="utf-8"))
    else:
        issue_ctx = IssueContext(
            repo_url=session.repo_url,
            repo_name=session.repo_full_name,
            issue_number=session.issue_number,
            title=f"Issue #{session.issue_number}",
            body="Workspace context.",
        )

    context_data = agent_gateway.build_context(local_path, issue_ctx)
    return AgentContextResponse(
        workspace_id=req.workspace_id,
        tech_stack=context_data.get("tech_stack", {}),
        relevant_files=context_data.get("relevant_files", []),
        issue_title=issue_ctx.title,
        issue_body=issue_ctx.body,
    )


@router.post("/suggest-fix", response_model=AgentSuggestFixResponse)
def suggest_agent_fix(
    req: AgentSuggestFixRequest,
    current_user: UserRecord = Depends(get_current_user),
    workspace_service: WorkspaceService = Depends(get_workspace_service),
    agent_gateway: AgentGatewayService = Depends(get_agent_gateway),
):
    """Calls oasis-agent's LLM routing to propose a unified diff patch for the issue."""
    session, local_path = workspace_service.get_workspace_or_404(req.workspace_id, current_user.id)
    issue_file = local_path / ".oasis-agent" / "issue.json"
    if issue_file.exists():
        issue_ctx = IssueContext.model_validate_json(issue_file.read_text(encoding="utf-8"))
    else:
        issue_ctx = IssueContext(
            repo_url=session.repo_url,
            repo_name=session.repo_full_name,
            issue_number=session.issue_number,
            title=f"Issue #{session.issue_number}",
            body="Workspace context.",
        )

    result = agent_gateway.suggest_fix(local_path, issue_ctx, req.instruction)
    return AgentSuggestFixResponse(
        workspace_id=req.workspace_id,
        proposal_diff=result.get("proposal_diff", ""),
        summary=result.get("summary", ""),
        applied=False,
    )


@router.post("/evaluate", response_model=GatekeeperVerdictResponse)
def evaluate_workspace_changes(
    req: AgentEvaluateRequest,
    current_user: UserRecord = Depends(get_current_user),
    workspace_service: WorkspaceService = Depends(get_workspace_service),
    agent_gateway: AgentGatewayService = Depends(get_agent_gateway),
):
    """Directly evaluates the current workspace diff using the Gatekeeper judge."""
    session, local_path = workspace_service.get_workspace_or_404(req.workspace_id, current_user.id)
    git_client = GitClient(local_path)
    diff_summary: GitDiffSummary = git_client.get_diff()

    issue_file = local_path / ".oasis-agent" / "issue.json"
    if issue_file.exists():
        issue_ctx = IssueContext.model_validate_json(issue_file.read_text(encoding="utf-8"))
    else:
        issue_ctx = IssueContext(
            repo_url=session.repo_url,
            repo_name=session.repo_full_name,
            issue_number=session.issue_number,
            title=f"Issue #{session.issue_number}",
            body="Workspace context.",
        )

    return agent_gateway.evaluate_diff(local_path, issue_ctx, diff_summary)
