"""
Meaningfulness Judge: Orchestrates heuristic pre-flight, test outcomes,
and semantic LLM evaluation against issue context.
"""

import logging
from typing import Optional
from oasis_agent.config import GatekeeperConfig
from oasis_agent.llm.client import LLMClient
from oasis_agent.llm.prompts import (
    MEANINGFULNESS_SYSTEM_PROMPT,
    MEANINGFULNESS_EVALUATION_PROMPT,
)
from oasis_agent.models import (
    EvaluationDimensionScore,
    GitDiffSummary,
    IssueContext,
    MeaningfulnessVerdict,
    TestRunResult,
)
from oasis_agent.evaluator.heuristics import run_heuristic_checks

logger = logging.getLogger("oasis_agent.judge")


class MeaningfulnessJudge:
    """Evaluates proposed pull request changes for genuine issue resolution."""

    def __init__(
        self,
        llm_client: LLMClient,
        gatekeeper_config: Optional[GatekeeperConfig] = None,
    ):
        self.llm_client = llm_client
        self.config = gatekeeper_config or GatekeeperConfig()

    def evaluate(
        self,
        issue: IssueContext,
        diff_summary: GitDiffSummary,
        test_results: Optional[TestRunResult] = None,
        tech_stack: str = "Generic",
    ) -> MeaningfulnessVerdict:
        """Run full evaluation pipeline: Heuristics -> Tests -> LLM Judge."""

        # 1. Deterministic Heuristic Checks
        heuristic_res = run_heuristic_checks(diff_summary.diff_content)
        if not heuristic_res.passed:
            logger.info(f"Heuristic check rejected change: {heuristic_res.reason}")
            return MeaningfulnessVerdict(
                meaningful=False,
                confidence=1.0,
                reasoning=heuristic_res.reason or "Change failed fast pre-flight heuristic checks.",
                missing_aspects=["Meaningful functional code edits"],
                dimension_scores={
                    "relevance": EvaluationDimensionScore(score=0.0, reasoning="Change has no functional relation to issue."),
                    "non_triviality": EvaluationDimensionScore(score=0.0, reasoning=heuristic_res.reason or "Trivial diff."),
                    "correctness": EvaluationDimensionScore(score=0.5, reasoning="Syntax neutral."),
                    "closure_likelihood": EvaluationDimensionScore(score=0.0, reasoning="Does not address the issue."),
                },
                recommended_action="REJECT",
                rejection_reason=heuristic_res.reason,
            )

        # 2. Local Test Suite Outcomes
        if test_results and test_results.executed and not test_results.passed:
            if self.config.reject_on_test_failure:
                reason = f"Local test suite failed with exit code {test_results.exit_code} after applying the patch."
                logger.info(f"Gatekeeper rejecting change due to test failure: {reason}")
                return MeaningfulnessVerdict(
                    meaningful=False,
                    confidence=0.95,
                    reasoning=f"{reason}\nOutput snippet:\n{test_results.output[:400]}",
                    missing_aspects=["Passing unit/integration tests"],
                    dimension_scores={
                        "relevance": EvaluationDimensionScore(score=0.7, reasoning="Diff attempted fix but broke test suite."),
                        "non_triviality": EvaluationDimensionScore(score=0.8, reasoning="Substantive changes attempted."),
                        "correctness": EvaluationDimensionScore(score=0.2, reasoning="Tests are failing."),
                        "closure_likelihood": EvaluationDimensionScore(score=0.1, reasoning="Cannot close issue with broken tests."),
                    },
                    recommended_action="REJECT",
                    rejection_reason=reason,
                )

        # 3. LLM-Based Semantic Evaluation
        test_summary = (
            f"Test Suite: {test_results.framework or 'Generic'}\nStatus: {'PASSED' if test_results.passed else 'FAILED'}\nDetails: {test_results.output[:500]}"
            if test_results and test_results.executed
            else "No local automated tests were executed."
        )

        comments_str = (
            "\n".join([f"- {c}" for c in issue.comments[:5]])
            if issue.comments
            else "No comments on this issue."
        )

        prompt = MEANINGFULNESS_EVALUATION_PROMPT.format(
            repo_name=issue.repo_name,
            tech_stack=tech_stack,
            issue_number=issue.issue_number,
            issue_title=issue.title,
            issue_body=issue.body or "No description provided.",
            issue_comments=comments_str,
            git_diff=diff_summary.diff_content[:10000],  # Keep prompt within comfortable context
            test_results=test_summary,
        )

        logger.info("Submitting diff to LLM gatekeeper for meaningfulness evaluation...")
        verdict, provider_used = self.llm_client.complete(
            prompt=prompt,
            task_type="meaningfulness_judgment",
            system_prompt=MEANINGFULNESS_SYSTEM_PROMPT,
            response_model=MeaningfulnessVerdict,
            temperature=0.1,
        )

        # 4. Enforce Confidence Threshold
        if verdict.confidence < self.config.confidence_threshold:
            logger.info(
                f"Verdict confidence ({verdict.confidence:.2f}) below threshold ({self.config.confidence_threshold:.2f}). Flagging for human review."
            )
            verdict.meaningful = False
            verdict.recommended_action = "FLAG_FOR_HUMAN_REVIEW"
            if not verdict.rejection_reason:
                verdict.rejection_reason = (
                    f"Confidence score ({verdict.confidence:.2f}) fell below required threshold ({self.config.confidence_threshold:.2f})."
                )
        elif not verdict.meaningful:
            verdict.recommended_action = "REJECT"
            if not verdict.rejection_reason:
                verdict.rejection_reason = verdict.reasoning[:200]
        else:
            verdict.recommended_action = "APPROVE_AND_PR"

        return verdict
