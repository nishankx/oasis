"""
Unit tests for Gatekeeper Evaluator, Heuristic checks, and Meaningfulness Judge.
"""

from oasis_agent.evaluator.heuristics import run_heuristic_checks
from oasis_agent.evaluator.judge import MeaningfulnessJudge
from oasis_agent.config import GatekeeperConfig, OasisConfig, ProviderConfig, TaskRouting
from oasis_agent.llm.client import LLMClient
from oasis_agent.llm.router import LLMRouter
from oasis_agent.models import (
    EvaluationDimensionScore,
    GitDiffSummary,
    IssueContext,
    MeaningfulnessVerdict,
    TestRunResult,
)
from oasis_agent.llm.providers import OpenAICompatibleProvider


class MockSucceedingProvider(OpenAICompatibleProvider):
    def __init__(self, name: str, return_content: str):
        super().__init__(name, "http://mock", "mock-model", "fake-key")
        self.return_content = return_content
        self.call_count = 0

    def call_chat_completion(self, messages, temperature=0.2, max_tokens=None):
        self.call_count += 1
        return {"content": self.return_content, "duration_ms": 15, "model": self.model}


def test_heuristic_empty_diff():
    res = run_heuristic_checks("")
    assert res.passed is False
    assert res.empty_diff is True


def test_heuristic_whitespace_only():
    diff = """--- a/math.py
+++ b/math.py
@@ -1,3 +1,3 @@
-def add(a, b):
+def add( a,   b ):
     return a + b
"""
    res = run_heuristic_checks(diff)
    assert res.passed is False
    assert res.whitespace_only is True


def test_heuristic_comment_only():
    diff = """--- a/math.py
+++ b/math.py
@@ -1,3 +1,4 @@
+# Added comment explaining function
 def add(a, b):
     return a + b
"""
    res = run_heuristic_checks(diff)
    assert res.passed is False
    assert res.comment_only is True


def test_heuristic_valid_code_diff():
    diff = """--- a/calculator.py
+++ b/calculator.py
@@ -10,3 +10,6 @@
 def divide(a, b):
+    if b == 0:
+        raise ValueError("Cannot divide by zero")
     return a / b
"""
    res = run_heuristic_checks(diff)
    assert res.passed is True


def test_judge_rejects_on_test_failure():
    # LLM client setup
    config = OasisConfig(
        gatekeeper=GatekeeperConfig(reject_on_test_failure=True),
        providers={"mock": ProviderConfig(base_url="http://mock", model="m", api_key_env="K")},
        llm_routing={"meaningfulness_judgment": TaskRouting(primary="mock")}
    )
    router = LLMRouter(config)
    mock_p = MockSucceedingProvider("mock", '{"meaningful": true, "confidence": 0.9, "reasoning": "Looks good", "dimension_scores": {}}')
    router.register_custom_provider("mock", mock_p)
    client = LLMClient(config=config, router=router)

    judge = MeaningfulnessJudge(client, gatekeeper_config=config.gatekeeper)
    issue = IssueContext(repo_url="http://repo", repo_name="owner/repo", issue_number=1, title="Fix div by zero")
    diff = GitDiffSummary(diff_content="""--- a/calc.py\n+++ b/calc.py\n@@ -1 +1,2 @@\n+x = 1\n""")
    failed_test = TestRunResult(executed=True, passed=False, output="FAILED test_calc.py", exit_code=1)

    verdict = judge.evaluate(issue=issue, diff_summary=diff, test_results=failed_test)
    assert verdict.meaningful is False
    assert verdict.recommended_action == "REJECT"
    assert "test suite failed" in verdict.reasoning.lower()


def test_judge_accepts_meaningful_change():
    config = OasisConfig(
        gatekeeper=GatekeeperConfig(confidence_threshold=0.70),
        providers={"mock": ProviderConfig(base_url="http://mock", model="m", api_key_env="K")},
        llm_routing={"meaningfulness_judgment": TaskRouting(primary="mock")}
    )
    router = LLMRouter(config)
    llm_payload = """
    {
      "meaningful": true,
      "confidence": 0.92,
      "reasoning": "Correctly prevents ZeroDivisionError and adds defensive validation",
      "missing_aspects": [],
      "dimension_scores": {
        "relevance": {"score": 0.95, "reasoning": "Direct fix for reported bug"},
        "non_triviality": {"score": 0.90, "reasoning": "Functional logic added"},
        "correctness": {"score": 0.95, "reasoning": "Clean syntax and handles edge cases"},
        "closure_likelihood": {"score": 0.90, "reasoning": "Fully resolves issue"}
      },
      "risks_or_side_effects": [],
      "recommended_action": "APPROVE_AND_PR"
    }
    """
    mock_p = MockSucceedingProvider("mock", llm_payload)
    router.register_custom_provider("mock", mock_p)
    client = LLMClient(config=config, router=router)

    judge = MeaningfulnessJudge(client, gatekeeper_config=config.gatekeeper)
    issue = IssueContext(repo_url="http://repo", repo_name="owner/repo", issue_number=10, title="Zero division in calculator")
    diff = GitDiffSummary(diff_content="""--- a/calc.py\n+++ b/calc.py\n@@ -5,3 +5,5 @@\n+    if b == 0:\n+        raise ZeroDivisionError()\n""")
    passed_test = TestRunResult(executed=True, passed=True, output="1 passed", exit_code=0)

    verdict = judge.evaluate(issue=issue, diff_summary=diff, test_results=passed_test)
    assert verdict.meaningful is True
    assert verdict.confidence >= 0.70
    assert verdict.recommended_action == "APPROVE_AND_PR"


def test_judge_flags_low_confidence_for_human_review():
    config = OasisConfig(
        gatekeeper=GatekeeperConfig(confidence_threshold=0.75),
        providers={"mock": ProviderConfig(base_url="http://mock", model="m", api_key_env="K")},
        llm_routing={"meaningfulness_judgment": TaskRouting(primary="mock")}
    )
    router = LLMRouter(config)
    # Model claims meaningful but confidence is 0.65 (< 0.75 threshold)
    llm_payload = """
    {
      "meaningful": true,
      "confidence": 0.65,
      "reasoning": "Might fix it, but edge cases might still be unhandled",
      "missing_aspects": ["Integration tests"],
      "dimension_scores": {
        "relevance": {"score": 0.7, "reasoning": "Addresses bug partially"},
        "non_triviality": {"score": 0.6, "reasoning": "Small edit"},
        "correctness": {"score": 0.6, "reasoning": "Not fully verified"},
        "closure_likelihood": {"score": 0.5, "reasoning": "Unclear"}
      },
      "risks_or_side_effects": ["Potential regression"],
      "recommended_action": "APPROVE_AND_PR"
    }
    """
    mock_p = MockSucceedingProvider("mock", llm_payload)
    router.register_custom_provider("mock", mock_p)
    client = LLMClient(config=config, router=router)

    judge = MeaningfulnessJudge(client, gatekeeper_config=config.gatekeeper)
    issue = IssueContext(repo_url="http://repo", repo_name="owner/repo", issue_number=10, title="Zero division in calculator")
    diff = GitDiffSummary(diff_content="""--- a/calc.py\n+++ b/calc.py\n@@ -1 +1,2 @@\n+fix = True\n""")

    verdict = judge.evaluate(issue=issue, diff_summary=diff)
    assert verdict.meaningful is False
    assert verdict.recommended_action == "FLAG_FOR_HUMAN_REVIEW"
    assert verdict.rejection_reason is not None
    assert "below" in verdict.rejection_reason.lower()
