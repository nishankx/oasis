"""
Deterministic heuristic checks for diff meaningfulness.
Instantly rejects empty diffs, whitespace-only changes, or comment-only changes.
"""

import re
from typing import List
from oasis_agent.models import HeuristicCheckResult


def is_comment_line(line: str) -> bool:
    """Check if a code line is purely a comment in common languages."""
    stripped = line.strip()
    if not stripped:
        return False
    comment_prefixes = ("#", "//", "/*", "*/", "*", "<!--", "--", "%", ";", "'''", '"""')
    return any(stripped.startswith(prefix) for prefix in comment_prefixes)


def run_heuristic_checks(diff_content: str) -> HeuristicCheckResult:
    """
    Run fast pre-flight heuristic checks on the unified diff.
    """
    if not diff_content or not diff_content.strip():
        return HeuristicCheckResult(
            passed=False,
            empty_diff=True,
            reason="Diff is completely empty. No changes were made."
        )

    lines = diff_content.splitlines()
    added_lines: List[str] = []
    removed_lines: List[str] = []

    for line in lines:
        if line.startswith("+++") or line.startswith("---") or line.startswith("@@"):
            continue
        if line.startswith("+"):
            added_lines.append(line[1:])
        elif line.startswith("-"):
            removed_lines.append(line[1:])

    # If no additions or deletions were parsed
    if not added_lines and not removed_lines:
        return HeuristicCheckResult(
            passed=False,
            empty_diff=True,
            reason="No code additions or deletions detected in git diff."
        )

    # Whitespace-only check
    def normalize_whitespace(text: str) -> str:
        return re.sub(r"\s+", "", text)

    added_squashed = "".join(normalize_whitespace(l) for l in added_lines)
    removed_squashed = "".join(normalize_whitespace(l) for l in removed_lines)

    if added_squashed == removed_squashed and added_squashed != "":
        return HeuristicCheckResult(
            passed=False,
            whitespace_only=True,
            reason="Proposed change contains only whitespace or line-break formatting changes."
        )

    # Comment-only check
    non_empty_additions = [l for l in added_lines if l.strip()]
    if non_empty_additions and all(is_comment_line(l) for l in non_empty_additions):
        # All added lines are comments
        non_empty_removals = [l for l in removed_lines if l.strip()]
        if not non_empty_removals or all(is_comment_line(l) for l in non_empty_removals):
            return HeuristicCheckResult(
                passed=False,
                comment_only=True,
                reason="Proposed change touches only comments or docstrings without functional modifications."
            )

    return HeuristicCheckResult(passed=True)
