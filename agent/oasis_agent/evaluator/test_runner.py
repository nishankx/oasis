"""
Local test runner: executes the project's test suite locally before gatekeeper evaluation.
"""

import logging
import subprocess
from pathlib import Path
from typing import List, Optional
from oasis_agent.models import TestRunResult
from oasis_agent.repo_context.inspector import RepoInspector

logger = logging.getLogger("oasis_agent.test_runner")


class LocalTestRunner:
    """Discovers and runs test suites in the target repository."""

    def __init__(self, repo_dir: Path, custom_command: Optional[List[str]] = None):
        self.repo_dir = Path(repo_dir)
        self.custom_command = custom_command

    def run_tests(self, timeout_seconds: int = 60) -> TestRunResult:
        """Run the repository test suite and return structured result."""
        command = self.custom_command
        framework = "Custom"
        if not command:
            inspector = RepoInspector(self.repo_dir)
            stack = inspector.detect_stack()
            command = stack.get("test_command")
            framework = stack["languages"][0] if stack["languages"] else "Unknown"

        if not command:
            logger.info("No test suite detected in repository. Skipping test run.")
            return TestRunResult(
                executed=False,
                passed=True,
                output="No automated test suite detected in repository.",
                exit_code=0,
                framework=None,
            )

        cmd_str = " ".join(command)
        logger.info(f"Running test suite: '{cmd_str}' in {self.repo_dir}...")

        try:
            res = subprocess.run(
                command,
                cwd=self.repo_dir,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_seconds,
            )
            passed = res.returncode == 0
            combined_output = ((res.stdout or "") + "\n" + (res.stderr or "")).strip()
            # Truncate if gigantic
            if len(combined_output) > 3000:
                combined_output = combined_output[:1500] + "\n...[truncated]...\n" + combined_output[-1500:]

            logger.info(f"Test suite finished with exit code {res.returncode} (passed={passed})")
            return TestRunResult(
                executed=True,
                passed=passed,
                output=combined_output,
                exit_code=res.returncode,
                framework=framework,
            )
        except subprocess.TimeoutExpired:
            logger.warning(f"Test suite timed out after {timeout_seconds}s")
            return TestRunResult(
                executed=True,
                passed=False,
                output=f"Test run timed out after {timeout_seconds} seconds.",
                exit_code=124,
                framework=framework,
            )
        except Exception as e:
            logger.warning(f"Failed to execute test command '{cmd_str}': {e}")
            return TestRunResult(
                executed=True,
                passed=False,
                output=f"Error executing test suite: {e}",
                exit_code=1,
                framework=framework,
            )
