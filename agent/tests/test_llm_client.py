"""
Unit tests for LLM provider abstraction, routing, failover, and JSON parser.
"""

import pytest
from pydantic import BaseModel
from oasis_agent.config import OasisConfig, ProviderConfig, TaskRouting
from oasis_agent.llm.client import LLMClient, LLMUnavailableError
from oasis_agent.llm.router import LLMRouter
from oasis_agent.llm.providers import OpenAICompatibleProvider, ProviderError
from oasis_agent.llm.parser import clean_llm_response, extract_json_string, parse_and_validate_json
from oasis_agent.models import MeaningfulnessVerdict


class DummyVerdict(BaseModel):
    meaningful: bool
    confidence: float
    reasoning: str


def test_clean_and_extract_json():
    # Test DeepSeek-R1 style output with <think> tokens and markdown fences
    raw = """
    <think>
    Thinking about the PR...
    It touches the right files.
    </think>
    Here is the evaluation:
    ```json
    {
        "meaningful": true,
        "confidence": 0.95,
        "reasoning": "Directly fixes bug"
    }
    ```
    Hope this helps!
    """
    json_str = extract_json_string(raw)
    assert "{" in json_str and "}" in json_str
    assert "<think>" not in json_str
    assert "```" not in json_str

    parsed, err = parse_and_validate_json(raw, target_schema=DummyVerdict)
    assert err is None
    assert parsed is not None
    assert parsed.meaningful is True
    assert parsed.confidence == 0.95


def test_router_prunes_missing_keys(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setenv("GOOGLE_API_KEY", "test-google-key")

    config = OasisConfig(
        providers={
            "openrouter_deepseek_r1": ProviderConfig(
                base_url="https://openrouter.ai/api/v1",
                model="deepseek/deepseek-r1:free",
                api_key_env="OPENROUTER_API_KEY",
            ),
            "google_gemini_flash": ProviderConfig(
                base_url="https://generativelanguage.googleapis.com/v1beta/openai",
                model="gemini-flash-latest",
                api_key_env="GOOGLE_API_KEY",
            ),
        },
        llm_routing={
            "meaningfulness_judgment": TaskRouting(
                primary="openrouter_deepseek_r1",
                fallback=["google_gemini_flash"]
            )
        }
    )

    router = LLMRouter(config)
    chain = router.get_routing_chain("meaningfulness_judgment")
    # openrouter is pruned because OPENROUTER_API_KEY is not set
    assert chain == ["google_gemini_flash"]


class MockFailingProvider(OpenAICompatibleProvider):
    def __init__(self, name: str, fail_with_rate_limit: bool = True):
        super().__init__(name, "http://mock", "mock-model", "fake-key")
        self.fail_with_rate_limit = fail_with_rate_limit
        self.call_count = 0

    def call_chat_completion(self, messages, temperature=0.2, max_tokens=None):
        self.call_count += 1
        if self.fail_with_rate_limit:
            raise ProviderError(f"{self.name} rate limited", status_code=429, is_rate_limit=True)
        raise ProviderError(f"{self.name} connection failed", is_server_error=True)


class MockSucceedingProvider(OpenAICompatibleProvider):
    def __init__(self, name: str, return_content: str):
        super().__init__(name, "http://mock", "mock-model", "fake-key")
        self.return_content = return_content
        self.call_count = 0

    def call_chat_completion(self, messages, temperature=0.2, max_tokens=None):
        self.call_count += 1
        return {"content": self.return_content, "duration_ms": 15, "model": self.model}


def test_llm_client_failover_success():
    config = OasisConfig(
        providers={
            "p1": ProviderConfig(base_url="http://p1", model="m1", api_key_env="K1", max_retries=1),
            "p2": ProviderConfig(base_url="http://p2", model="m2", api_key_env="K2", max_retries=1),
        },
        llm_routing={
            "codebase_search": TaskRouting(primary="p1", fallback=["p2"])
        }
    )
    router = LLMRouter(config)
    # Register mock providers directly
    p1 = MockFailingProvider("p1", fail_with_rate_limit=True)
    p2 = MockSucceedingProvider("p2", return_content="Search results found")
    router.register_custom_provider("p1", p1)
    router.register_custom_provider("p2", p2)

    client = LLMClient(config=config, router=router)
    result, provider_used = client.complete("Search for utils", task_type="codebase_search")

    assert provider_used == "p2"
    assert result == "Search results found"
    assert client.metrics.failover_count == 1
    assert "calls to p1" in client.metrics.summary_string()
    assert "calls to p2" in client.metrics.summary_string()


def test_llm_client_all_fail():
    config = OasisConfig(
        providers={
            "p1": ProviderConfig(base_url="http://p1", model="m1", api_key_env="K1", max_retries=0),
        },
        llm_routing={
            "codebase_search": TaskRouting(primary="p1", fallback=[])
        }
    )
    router = LLMRouter(config)
    p1 = MockFailingProvider("p1", fail_with_rate_limit=True)
    router.register_custom_provider("p1", p1)

    client = LLMClient(config=config, router=router)
    with pytest.raises(LLMUnavailableError) as exc_info:
        client.complete("Search for utils", task_type="codebase_search")

    assert "All LLM providers failed" in str(exc_info.value)
