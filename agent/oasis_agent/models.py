"""
Pydantic Domain Models for oasis-agent.
"""

from enum import Enum
from typing import Dict, List, Optional, Literal
from pydantic import BaseModel, Field


class TaskType(str, Enum):
    CONTEXT_MAPPING = "context_mapping"
    CODEBASE_SEARCH = "codebase_search"
    CODE_EDITING = "code_editing"
    MEANINGFULNESS_JUDGMENT = "meaningfulness_judgment"
    PR_DESCRIPTION_GENERATION = "pr_description_generation"
    REVIEW_REPORT_GENERATION = "review_report_generation"


class CodeFileEdit(BaseModel):
    file_path: str = Field(..., description="Relative file path in the repository")
    new_content: str = Field(..., description="Full updated content of the file")
    explanation: str = Field(default="", description="Why this file was modified")


class CodeEditsProposal(BaseModel):
    edits: List[CodeFileEdit] = Field(default_factory=list, description="List of file modifications")
    summary: str = Field(default="", description="Summary of the remediation")


class RunStatus(str, Enum):
    COMPLETED_PR_OPENED = "completed_pr_opened"
    COMPLETED_REJECTED = "completed_rejected"
    COMPLETED_DRY_RUN = "completed_dry_run"
    FLAGGED_HUMAN_REVIEW = "flagged_human_review"
    LLM_UNAVAILABLE = "llm_unavailable"
    ERROR = "error"


class EvaluationDimensionScore(BaseModel):
    score: float = Field(..., ge=0.0, le=1.0, description="Score from 0.0 to 1.0")
    reasoning: str = Field(..., description="Explanation for this dimension score")


class MeaningfulnessVerdict(BaseModel):
    meaningful: bool = Field(..., description="True if the patch is meaningful and addresses the issue")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score from 0.0 to 1.0")
    reasoning: str = Field(..., description="Detailed explanation of the verdict")
    missing_aspects: List[str] = Field(default_factory=list, description="Aspects of the issue not addressed")
    dimension_scores: Dict[str, EvaluationDimensionScore] = Field(
        default_factory=dict,
        description="Detailed scores across relevance, non_triviality, correctness, closure_likelihood"
    )
    risks_or_side_effects: List[str] = Field(default_factory=list, description="Identified risks or regressions")
    recommended_action: Literal["APPROVE_AND_PR", "REJECT", "FLAG_FOR_HUMAN_REVIEW"] = Field(
        default="REJECT",
        description="Action recommended by the gatekeeper"
    )
    rejection_reason: Optional[str] = Field(default=None, description="Summary reason if rejected")


class HeuristicCheckResult(BaseModel):
    passed: bool = True
    empty_diff: bool = False
    whitespace_only: bool = False
    comment_only: bool = False
    revert_only: bool = False
    reason: Optional[str] = None


class TestRunResult(BaseModel):
    __test__ = False
    executed: bool = False
    passed: bool = True
    output: str = ""
    exit_code: int = 0
    framework: Optional[str] = None


class GitDiffSummary(BaseModel):
    files_changed: List[str] = Field(default_factory=list)
    insertions: int = 0
    deletions: int = 0
    diff_content: str = ""


class IssueContext(BaseModel):
    repo_url: str
    repo_name: str
    issue_number: int
    title: str
    body: str = ""
    labels: List[str] = Field(default_factory=list)
    comments: List[str] = Field(default_factory=list)
    author: Optional[str] = None


class LLMCallRecord(BaseModel):
    provider: str
    model: str
    task_type: str
    success: bool
    duration_ms: int = 0
    failover_from: Optional[str] = None
    error: Optional[str] = None


class RunMetrics(BaseModel):
    calls_by_provider: Dict[str, int] = Field(default_factory=dict)
    failover_count: int = 0
    total_calls: int = 0
    records: List[LLMCallRecord] = Field(default_factory=list)

    def record_call(self, provider: str, model: str, task_type: str, success: bool,
                    duration_ms: int = 0, failover_from: Optional[str] = None, error: Optional[str] = None):
        self.total_calls += 1
        self.calls_by_provider[provider] = self.calls_by_provider.get(provider, 0) + 1
        if failover_from:
            self.failover_count += 1
        self.records.append(
            LLMCallRecord(
                provider=provider,
                model=model,
                task_type=task_type,
                success=success,
                duration_ms=duration_ms,
                failover_from=failover_from,
                error=error
            )
        )

    def summary_string(self) -> str:
        parts = [f"{count} calls to {provider}" for provider, count in self.calls_by_provider.items()]
        if self.failover_count > 0:
            parts.append(f"{self.failover_count} failovers")
        return ", ".join(parts) if parts else "0 LLM calls"


class ReviewReport(BaseModel):
    run_id: str
    timestamp: str
    repo_url: str
    issue_number: int
    issue_title: str
    status: RunStatus
    meaningfulness: MeaningfulnessVerdict
    diff_summary: GitDiffSummary
    test_results: Optional[TestRunResult] = None
    pr_url: Optional[str] = None
    pr_number: Optional[int] = None
    branch_name: Optional[str] = None
    metrics: RunMetrics = Field(default_factory=RunMetrics)
    ci_status: Optional[str] = None
    dry_run: bool = False
