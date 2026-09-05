"""
Pull Request and Webhook models.
"""

from __future__ import annotations
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from oasis_backend.models.agent import GatekeeperVerdictResponse


class PushPRRequest(BaseModel):
    workspace_id: str
    custom_commit_message: Optional[str] = None
    dry_run: bool = False
    force: bool = False


class PushPRResponse(BaseModel):
    success: bool
    status: str  # approved_pr_opened, rejected, flagged_human_review, dry_run
    pr_url: Optional[str] = None
    pr_number: Optional[int] = None
    branch_name: Optional[str] = None
    gatekeeper: GatekeeperVerdictResponse
    gatekeeper_verdict: Optional[GatekeeperVerdictResponse] = None
    ci_status: Optional[str] = None

    def model_post_init(self, __context: Any) -> None:
        if self.gatekeeper_verdict is None and self.gatekeeper is not None:
            self.gatekeeper_verdict = self.gatekeeper


class PRStatusResponse(BaseModel):
    pr_id: str
    workspace_id: Optional[str] = None
    repo_full_name: str
    pr_number: int
    pr_url: str
    head_branch: str
    status: str  # open, merged, closed, rejected
    ci_status: Optional[str] = None
    merged_at: Optional[str] = None
    gatekeeper: Optional[Dict[str, Any]] = None
    created_at: str
    updated_at: str


class WebhookEventResponse(BaseModel):
    handled: bool
    event_type: str
    action: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
