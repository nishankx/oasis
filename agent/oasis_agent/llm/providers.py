"""
Low-level OpenAI-compatible HTTP client adapter.
Connects to OpenRouter, Groq, Google AI Studio, and NVIDIA NIM.
"""

import time
from typing import Any, Dict, List, Optional
import httpx


class ProviderError(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None, is_rate_limit: bool = False, is_server_error: bool = False, is_timeout: bool = False):
        super().__init__(message)
        self.status_code = status_code
        self.is_rate_limit = is_rate_limit
        self.is_server_error = is_server_error
        self.is_timeout = is_timeout


class OpenAICompatibleProvider:
    """Lightweight caller for OpenAI-compatible Chat Completion endpoints."""

    def __init__(
        self,
        name: str,
        base_url: str,
        model: str,
        api_key: str,
        timeout_seconds: int = 35,
    ):
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    def call_chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Execute a synchronous HTTP chat completion request."""
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Specific headers for OpenRouter
        if "openrouter.ai" in self.base_url:
            headers["HTTP-Referer"] = "https://github.com/oasis-agent"
            headers["X-Title"] = "oasis-agent"

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens

        start_time = time.perf_counter()
        try:
            with httpx.Client(timeout=float(self.timeout_seconds)) as client:
                response = client.post(url, headers=headers, json=payload)
                duration_ms = int((time.perf_counter() - start_time) * 1000)

                # Check rate limits (429)
                if response.status_code == 429:
                    raise ProviderError(
                        f"Rate limit exceeded (HTTP 429) from {self.name}: {response.text[:200]}",
                        status_code=429,
                        is_rate_limit=True,
                    )
                # Check server errors (5xx)
                if 500 <= response.status_code < 600:
                    raise ProviderError(
                        f"Server error (HTTP {response.status_code}) from {self.name}: {response.text[:200]}",
                        status_code=response.status_code,
                        is_server_error=True,
                    )
                # Check other HTTP errors (401, 403, 400, etc.)
                if response.status_code >= 400:
                    raise ProviderError(
                        f"HTTP {response.status_code} from {self.name}: {response.text[:200]}",
                        status_code=response.status_code,
                    )

                data = response.json()
                choice = data.get("choices", [{}])[0]
                content = choice.get("message", {}).get("content", "")
                
                return {
                    "content": content,
                    "duration_ms": duration_ms,
                    "model": data.get("model", self.model),
                    "raw": data,
                }

        except httpx.TimeoutException as e:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            raise ProviderError(
                f"Timeout after {self.timeout_seconds}s from {self.name}: {e}",
                is_timeout=True,
            ) from e
        except httpx.RequestError as e:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            raise ProviderError(
                f"Network request error from {self.name}: {e}",
                is_server_error=True,
            ) from e
