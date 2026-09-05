"""
Codebase inspector: detects tech stack, dependencies, test framework,
and builds clean directory tree representations.
"""

from pathlib import Path
from typing import Dict, List, Optional


IGNORED_DIRS = {
    ".git",
    ".oasis-agent",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    "dist",
    "build",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "target",
}


class RepoInspector:
    """Inspects a repository's architecture, dependencies, and test setup."""

    def __init__(self, repo_dir: Path):
        self.repo_dir = Path(repo_dir)

    def detect_stack(self) -> Dict[str, any]:
        """Identify languages, frameworks, and default test runner command."""
        stack: Dict[str, any] = {
            "languages": [],
            "frameworks": [],
            "test_command": None,
            "manifest_files": [],
        }

        # Python
        if (self.repo_dir / "pyproject.toml").exists() or (self.repo_dir / "setup.py").exists() or (self.repo_dir / "requirements.txt").exists():
            stack["languages"].append("Python")
            stack["manifest_files"].extend(
                [f for f in ["pyproject.toml", "setup.py", "requirements.txt"] if (self.repo_dir / f).exists()]
            )
            stack["test_command"] = ["pytest"]

        # JavaScript / TypeScript / Node.js
        if (self.repo_dir / "package.json").exists():
            stack["languages"].append("JavaScript/TypeScript")
            stack["manifest_files"].append("package.json")
            if not stack["test_command"]:
                stack["test_command"] = ["npm", "test"]

        # Rust
        if (self.repo_dir / "Cargo.toml").exists():
            stack["languages"].append("Rust")
            stack["manifest_files"].append("Cargo.toml")
            if not stack["test_command"]:
                stack["test_command"] = ["cargo", "test"]

        # Go
        if (self.repo_dir / "go.mod").exists():
            stack["languages"].append("Go")
            stack["manifest_files"].append("go.mod")
            if not stack["test_command"]:
                stack["test_command"] = ["go", "test", "./..."]

        # Java
        if (self.repo_dir / "pom.xml").exists():
            stack["languages"].append("Java")
            stack["manifest_files"].append("pom.xml")
            if not stack["test_command"]:
                stack["test_command"] = ["mvn", "test"]
        elif (self.repo_dir / "build.gradle").exists() or (self.repo_dir / "build.gradle.kts").exists():
            stack["languages"].append("Java/Kotlin")
            if not stack["test_command"]:
                stack["test_command"] = ["./gradlew", "test"]

        if not stack["languages"]:
            stack["languages"].append("Generic")

        return stack

    def build_file_tree(self, max_depth: int = 4, max_files: int = 150) -> List[str]:
        """Generate a list of relative file paths in the repository."""
        tree = []
        count = 0

        for path in sorted(self.repo_dir.rglob("*")):
            # Check if any parent is in IGNORED_DIRS
            parts = set(path.relative_to(self.repo_dir).parts)
            if parts.intersection(IGNORED_DIRS):
                continue
            if path.is_file():
                tree.append(str(path.relative_to(self.repo_dir)).replace("\\", "/"))
                count += 1
                if count >= max_files:
                    tree.append(f"... (truncated after {max_files} files)")
                    break

        return tree

    def get_summary_context(self) -> str:
        """Produce markdown string summarizing detected stack and directory layout."""
        stack = self.detect_stack()
        files = self.build_file_tree()
        langs = ", ".join(stack["languages"])
        manifests = ", ".join(stack["manifest_files"]) or "None"
        test_cmd = " ".join(stack["test_command"]) if stack["test_command"] else "None detected"

        summary = [
            f"- Languages: {langs}",
            f"- Manifests: {manifests}",
            f"- Test Runner: `{test_cmd}`",
            f"- File Count: {len(files)} files indexed",
            "\n**Codebase Structure:**",
            "```",
        ]
        summary.extend(files[:50])
        if len(files) > 50:
            summary.append(f"... and {len(files) - 50} more files")
        summary.append("```")

        return "\n".join(summary)
