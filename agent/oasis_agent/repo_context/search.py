"""
Codebase search primitives: grep / keyword-based file relevance ranking.
"""

import re
from pathlib import Path
from typing import List, Tuple
from oasis_agent.models import IssueContext
from oasis_agent.repo_context.inspector import IGNORED_DIRS


class CodebaseSearcher:
    """Finds files most relevant to an issue using keyword/token matching."""

    def __init__(self, repo_dir: Path):
        self.repo_dir = Path(repo_dir)

    def extract_keywords(self, issue: IssueContext) -> List[str]:
        """Extract meaningful identifiers and words from issue title and body."""
        raw_text = f"{issue.title} {issue.body} {' '.join(issue.labels)}"
        # Extract code-like identifiers (e.g. CamelCase, snake_case, or dotted names)
        identifiers = re.findall(r"\b[A-Za-z_][A-Za-z0-9_\.]{2,}\b", raw_text)
        # Filter common stopwords
        stopwords = {
            "the", "and", "for", "that", "this", "with", "from", "have",
            "not", "when", "then", "issue", "bug", "fix", "please", "error",
            "fail", "failing", "does", "expected", "actual", "reproduce"
        }
        keywords = [w.lower() for w in identifiers if w.lower() not in stopwords]
        # Return unique keywords preserving order
        return list(dict.fromkeys(keywords))[:15]

    def rank_relevant_files(self, keywords: List[str], top_k: int = 5) -> List[Tuple[str, int]]:
        """
        Rank codebase files by relevance to the extracted keywords.
        Returns: list of (relative_file_path, score)
        """
        scores: dict[str, int] = {}

        for path in self.repo_dir.rglob("*"):
            parts = set(path.relative_to(self.repo_dir).parts)
            if parts.intersection(IGNORED_DIRS) or not path.is_file():
                continue

            # Exclude large binaries or assets
            if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".ico", ".pdf", ".zip", ".tar", ".lock"}:
                continue

            rel_path = str(path.relative_to(self.repo_dir)).replace("\\", "/")
            score = 0

            # Match against filename and path components (higher weight)
            for kw in keywords:
                if kw in rel_path.lower():
                    score += 5

            # Match against file content
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
                for kw in keywords:
                    # Match function/class definitions (high weight)
                    def_matches = len(re.findall(rf"\b(def|class|fn|function)\s+[A-Za-z0-9_]*{re.escape(kw)}", content, re.IGNORECASE))
                    score += def_matches * 4

                    # Regular occurrences (capped)
                    occ = len(re.findall(rf"\b{re.escape(kw)}\b", content, re.IGNORECASE))
                    score += min(occ, 5)
            except Exception:
                continue

            if score > 0:
                scores[rel_path] = score

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return ranked[:top_k]
