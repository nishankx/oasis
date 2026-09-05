"""
Agent Gateway service: direct programmatic wrapper around oasis-agent core modules.
Stateless library calls for context building, AI fix suggestions, and gatekeeper evaluation.
"""

from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List, Optional
from oasis_agent.config import OasisConfig, load_config
from oasis_agent.evaluator.judge import MeaningfulnessJudge
from oasis_agent.llm.client import LLMClient
from oasis_agent.models import (
    GitDiffSummary,
    IssueContext,
    MeaningfulnessVerdict,
    RunMetrics,
    TestRunResult,
)
from oasis_agent.repo_context import CodebaseEditor, CodebaseSearcher, RepoInspector
from oasis_backend.config import settings
from oasis_backend.models.agent import GatekeeperVerdictResponse


class AgentGatewayService:
    def __init__(self, config_path: Optional[str] = None):
        cfg_path = config_path or settings.oasis_agent_config_path
        # Resolve config path relative to workspace root if needed
        p = Path(cfg_path)
        if not p.is_absolute():
            p = Path.cwd() / p
        self.config: OasisConfig = load_config(str(p) if p.exists() else None)
        self.metrics = RunMetrics()
        self.llm_client = LLMClient(config=self.config, metrics=self.metrics)
        self.judge = MeaningfulnessJudge(self.llm_client, gatekeeper_config=self.config.gatekeeper)

    def build_context(
        self,
        local_path: Path,
        issue_ctx: IssueContext,
    ) -> Dict[str, Any]:
        """
        Uses RepoInspector and CodebaseSearcher to detect tech stack and rank top relevant files.
        """
        local_path = Path(local_path).resolve()
        inspector = RepoInspector(local_path)
        stack_info = inspector.detect_stack()

        searcher = CodebaseSearcher(local_path)
        keywords = searcher.extract_keywords(issue_ctx)
        ranked = searcher.rank_relevant_files(keywords, top_k=5)
        relevant_files = [file_path for file_path, _ in ranked]

        return {
            "tech_stack": stack_info,
            "relevant_files": relevant_files,
            "keywords": keywords,
        }

    def suggest_fix(
        self,
        local_path: Path,
        issue_ctx: IssueContext,
        instruction: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Gathers context from relevant files and prompts LLM for a recommended diff patch.
        """
        local_path = Path(local_path).resolve()
        editor = CodebaseEditor(local_path)
        searcher = CodebaseSearcher(local_path)
        keywords = searcher.extract_keywords(issue_ctx)
        ranked = searcher.rank_relevant_files(keywords, top_k=3)

        files_context_parts = []
        for file_path, _ in ranked:
            try:
                content = editor.read_file(file_path)
                files_context_parts.append(f"### File: {file_path}\n```\n{content[:2000]}\n```")
            except Exception:
                continue

        files_context = "\n\n".join(files_context_parts) or "No specific files matched."
        custom_inst = f"\nAdditional Instructions: {instruction}" if instruction else ""

        prompt = (
            f"You are an expert software engineer resolving a GitHub issue.\n\n"
            f"Issue #{issue_ctx.issue_number}: {issue_ctx.title}\n"
            f"Description:\n{issue_ctx.body}\n{custom_inst}\n\n"
            f"Codebase Context:\n{files_context}\n\n"
            f"Provide a unified git diff proposal that fixes the issue directly and concisely. "
            f"Only output the diff or the code changes with filename headers."
        )

        try:
            proposal, provider = self.llm_client.complete(
                prompt=prompt,
                task_type="code_editing",
            )
            return {
                "proposal_diff": proposal,
                "summary": f"Generated using {provider} via oasis-agent routing.",
            }
        except Exception as e:
            return {
                "proposal_diff": f"# Could not generate AI proposal: {e}",
                "summary": f"LLM error: {e}",
            }

    def evaluate_diff(
        self,
        local_path: Path,
        issue_ctx: IssueContext,
        diff_summary: GitDiffSummary,
        test_results: Optional[TestRunResult] = None,
    ) -> GatekeeperVerdictResponse:
        """
        Evaluates the code diff against the target issue using oasis-agent's MeaningfulnessJudge.
        """
        local_path = Path(local_path).resolve()
        inspector = RepoInspector(local_path)
        stack_info = inspector.detect_stack()
        tech_stack_desc = ", ".join(stack_info.get("languages", [])) or "General"

        try:
            verdict: MeaningfulnessVerdict = self.judge.evaluate(
                issue=issue_ctx,
                diff_summary=diff_summary,
                test_results=test_results,
                tech_stack=tech_stack_desc,
            )
            dim_scores = getattr(verdict, "dimension_scores", {}) or {}
            def _extract_pct(dim_name: str) -> int:
                d = dim_scores.get(dim_name)
                if d and hasattr(d, "score") and d.score is not None:
                    return int(d.score * 100)
                return int(verdict.confidence * 100)

            from oasis_backend.models.agent import GatekeeperDimensions
            dims = GatekeeperDimensions(
                relevance=_extract_pct("relevance"),
                non_triviality=_extract_pct("non_triviality"),
                correctness=_extract_pct("correctness"),
                closure_likelihood=_extract_pct("closure_likelihood"),
            )

            is_approved = verdict.meaningful and verdict.recommended_action == "APPROVE_AND_PR"
            return GatekeeperVerdictResponse(
                meaningful=verdict.meaningful,
                confidence=verdict.confidence,
                reasoning=verdict.reasoning,
                recommended_action=verdict.recommended_action,
                rejection_reason=verdict.rejection_reason,
                approved=is_approved,
                confidence_score=int(verdict.confidence * 100),
                dimensions=dims,
                suggestions=getattr(verdict, "missing_aspects", []) or [],
            )
        except Exception as e:
            # Fallback safe verdict if LLM providers are unavailable
            from oasis_backend.models.agent import GatekeeperDimensions
            return GatekeeperVerdictResponse(
                meaningful=False,
                confidence=0.0,
                reasoning=f"Gatekeeper LLM evaluation unavailable: {e}",
                recommended_action="REJECT",
                rejection_reason=f"LLM providers unavailable: {e}",
                approved=False,
                confidence_score=0,
                dimensions=GatekeeperDimensions(),
                suggestions=[],
            )
