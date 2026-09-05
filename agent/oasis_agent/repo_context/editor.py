"""
Reversible file editing primitives and patch tracker.
Supports read_file, list_files, search_codebase, edit_file, create_file,
and complete rollback.
"""

import difflib
from pathlib import Path
from typing import Dict, List, Optional
from oasis_agent.models import GitDiffSummary


class CodebaseEditor:
    """Manages diff-based, reversible edits to files in a repository."""

    def __init__(self, repo_dir: Path):
        self.repo_dir = Path(repo_dir).resolve()
        self._original_contents: Dict[str, Optional[str]] = {}
        self._created_files: List[str] = []

    def _resolve(self, rel_path: str) -> Path:
        p = (self.repo_dir / rel_path).resolve()
        # Security check: prevent directory traversal
        if not str(p).startswith(str(self.repo_dir)):
            raise ValueError(f"Path traversal detected: {rel_path}")
        return p

    def read_file(self, rel_path: str) -> str:
        """Read content of a file within the repo."""
        p = self._resolve(rel_path)
        if not p.exists():
            raise FileNotFoundError(f"File not found: {rel_path}")
        return p.read_text(encoding="utf-8", errors="replace")

    def list_files(self, subdir: str = "") -> List[str]:
        """List files in repository or subdirectory."""
        target = self._resolve(subdir) if subdir else self.repo_dir
        if not target.exists():
            return []
        files = []
        for p in target.rglob("*"):
            if p.is_file() and ".git" not in p.parts:
                files.append(str(p.relative_to(self.repo_dir)).replace("\\", "/"))
        return files

    def search_codebase(self, query: str) -> List[dict]:
        """Search across text files for query."""
        results = []
        for rel in self.list_files():
            try:
                content = self.read_file(rel)
                for line_no, line in enumerate(content.splitlines(), start=1):
                    if query.lower() in line.lower():
                        results.append({"file": rel, "line": line_no, "content": line.strip()})
            except Exception:
                continue
        return results

    def edit_file(self, rel_path: str, new_content: str) -> str:
        """
        Overwrite an existing file, storing the original for reversible rollback.
        Returns unified diff string.
        """
        p = self._resolve(rel_path)
        rel_key = str(p.relative_to(self.repo_dir)).replace("\\", "/")

        if not p.exists():
            raise FileNotFoundError(f"Cannot edit non-existent file '{rel_path}'. Use create_file instead.")

        if rel_key not in self._original_contents:
            self._original_contents[rel_key] = p.read_text(encoding="utf-8", errors="replace")

        old_text = self._original_contents[rel_key]
        p.write_text(new_content, encoding="utf-8")

        diff = difflib.unified_diff(
            old_text.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile=f"a/{rel_key}",
            tofile=f"b/{rel_key}",
        )
        return "".join(diff)

    def create_file(self, rel_path: str, content: str) -> str:
        """Create a new file within the repo, marking it for rollback if aborted."""
        p = self._resolve(rel_path)
        rel_key = str(p.relative_to(self.repo_dir)).replace("\\", "/")

        p.parent.mkdir(parents=True, exist_ok=True)
        if p.exists() and rel_key not in self._original_contents:
            self._original_contents[rel_key] = p.read_text(encoding="utf-8", errors="replace")
        elif not p.exists():
            self._original_contents[rel_key] = None  # None indicates file didn't exist
            self._created_files.append(rel_key)

        p.write_text(content, encoding="utf-8")

        diff = difflib.unified_diff(
            [],
            content.splitlines(keepends=True),
            fromfile="/dev/null",
            tofile=f"b/{rel_key}",
        )
        return "".join(diff)

    def rollback_all(self):
        """Revert all edits and remove newly created files."""
        for rel_key, original in self._original_contents.items():
            p = self._resolve(rel_key)
            if original is None:
                if p.exists():
                    p.unlink()
            else:
                p.write_text(original, encoding="utf-8")
        self._original_contents.clear()
        self._created_files.clear()

    def compute_diff_summary(self) -> GitDiffSummary:
        """Compute unified diff summary of all active changes."""
        all_diffs = []
        files_changed = []
        insertions = 0
        deletions = 0

        for rel_key, original in self._original_contents.items():
            p = self._resolve(rel_key)
            current_text = p.read_text(encoding="utf-8", errors="replace") if p.exists() else ""
            old_text = original if original is not None else ""

            if old_text == current_text:
                continue

            files_changed.append(rel_key)
            diff_lines = list(
                difflib.unified_diff(
                    old_text.splitlines(keepends=True),
                    current_text.splitlines(keepends=True),
                    fromfile=f"a/{rel_key}" if original is not None else "/dev/null",
                    tofile=f"b/{rel_key}",
                )
            )
            for line in diff_lines:
                if line.startswith("+") and not line.startswith("+++"):
                    insertions += 1
                elif line.startswith("-") and not line.startswith("---"):
                    deletions += 1

            all_diffs.extend(diff_lines)

        return GitDiffSummary(
            files_changed=files_changed,
            insertions=insertions,
            deletions=deletions,
            diff_content="".join(all_diffs),
        )
