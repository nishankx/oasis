"""
Agent gateway request and response models.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AgentContextRequest(BaseModel):
    workspace_id: str


class AgentContextResponse(BaseModel):
    workspace_id: str
    tech_stack: Dict[str, Any] = Field(default_factory=dict)
    relevant_files: List[str] = Field(default_factory=list)
    issue_title: str
    issue_body: str


class AgentSuggestFixRequest(BaseModel):
    workspace_id: str
    instruction: Optional[str] = None


class AgentSuggestFixResponse(BaseModel):
    workspace_id: str
    proposal_diff: str
    summary: str
    applied: bool = False


class AgentEvaluateRequest(BaseModel):
    workspace_id: str


class GatekeeperDimensions(BaseModel):
    relevance: int = 0
    non_triviality: int = 0
    correctness: int = 0
    closure_likelihood: int = 0


class GatekeeperVerdictResponse(BaseModel):
    meaningful: bool
    confidence: float
    reasoning: str
    recommended_action: str  # APPROVE_AND_PR, REJECT, FLAG_FOR_HUMAN_REVIEW
    rejection_reason: Optional[str] = None
    approved: bool = False
    confidence_score: int = 0
    dimensions: GatekeeperDimensions = Field(default_factory=GatekeeperDimensions)
    suggestions: List[str] = Field(default_factory=list)

    def model_post_init(self, __context: Any) -> None:
        if not self.approved and self.meaningful:
            self.approved = True
        if self.confidence_score == 0 and self.confidence > 0:
            self.confidence_score = int(self.confidence * 100)
