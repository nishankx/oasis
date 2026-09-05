"""
Markdown comment generators for GitHub PRs and Issues.
"""

from oasis_agent.models import ReviewReport


def generate_pr_comment(report: ReviewReport) -> str:
    """Generate structured PR review comment signed off as 'Reviewed by oasis-agent'."""
    v = report.meaningfulness
    status_emoji = "✅" if v.meaningful else "❌"

    dimension_rows = []
    for dim_name, score_obj in v.dimension_scores.items():
        bar_len = int(score_obj.score * 10)
        progress_bar = "█" * bar_len + "░" * (10 - bar_len)
        dimension_rows.append(
            f"| **{dim_name.capitalize()}** | `{progress_bar}` {score_obj.score:.2f} | {score_obj.reasoning} |"
        )
    dim_table = "\n".join(dimension_rows)

    missing_str = (
        "\n".join([f"- {m}" for m in v.missing_aspects]) if v.missing_aspects else "_None identified_"
    )
    risks_str = (
        "\n".join([f"- {r}" for r in v.risks_or_side_effects]) if v.risks_or_side_effects else "_None identified_"
    )
    test_str = (
        f"{'Passed' if report.test_results.passed else 'Failed'} ({report.test_results.framework or 'Generic'})"
        if report.test_results and report.test_results.executed
        else "Skipped / None configured"
    )

    return f"""## {status_emoji} Pre-Flight Meaningfulness Evaluation

**Verdict:** `{'MEANINGFUL (Approved)' if v.meaningful else 'REJECTED'}`  
**Confidence Score:** `{v.confidence:.2f}`  
**Test Suite:** `{test_str}`

### Dimension Analysis
| Dimension | Score | Assessment |
| :--- | :--- | :--- |
{dim_table}

### Gatekeeper Reasoning
> {v.reasoning}

### Remaining Aspects / Risks
- **Unaddressed Aspects:**
{missing_str}
- **Identified Risks:**
{risks_str}

---
*Autonomous Gatekeeper Review generated and verified by **oasis-agent***
"""


def generate_issue_rejection_comment(report: ReviewReport) -> str:
    """Generate comment for issue if agent aborted without opening PR."""
    v = report.meaningfulness
    return f"""### ⚠️ oasis-agent: Automated Resolution Report

oasis-agent attempted to analyze and propose a code change for this issue, but the proposed change was rejected by the **Meaningfulness Gatekeeper** before opening a PR.

**Reason:** {v.rejection_reason or v.reasoning}  
**Confidence:** {v.confidence:.2f}  
**Recommended Action:** {v.recommended_action}

#### What was missing:
{chr(10).join([f"- {m}" for m in v.missing_aspects]) if v.missing_aspects else "- No specific aspects identified."}

_No branch was pushed or PR opened to maintain codebase quality._
"""
