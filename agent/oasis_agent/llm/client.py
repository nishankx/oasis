"""
Abstracted LLM Client with multi-provider failover, exponential backoff,
call metrics tracking, and resilient structured output validation.
"""

import logging
import time
from typing import Any, Dict, List, Optional, Type, TypeVar
from pydantic import BaseModel

from oasis_agent.config import OasisConfig, load_config
from oasis_agent.models import RunMetrics, TaskType
from oasis_agent.llm.providers import OpenAICompatibleProvider, ProviderError
from oasis_agent.llm.router import LLMRouter
from oasis_agent.llm.parser import parse_and_validate_json
from oasis_agent.llm.prompts import JSON_STRICT_RETRY_PROMPT

logger = logging.getLogger("oasis_agent.llm")

T = TypeVar("T", bound=BaseModel)


class LLMUnavailableError(Exception):
    """Raised when all candidate providers in the failover chain fail."""
    def __init__(self, task_type: str, chain_attempted: List[str], last_error: Optional[str] = None):
        msg = f"All LLM providers failed for task '{task_type}'. Attempted chain: {chain_attempted}. Last error: {last_error}"
        super().__init__(msg)
        self.task_type = task_type
        self.chain_attempted = chain_attempted
        self.last_error = last_error


class LLMClient:
    """Unified interface for executing LLM completions with transparent multi-provider failover."""

    def __init__(
        self,
        config: Optional[OasisConfig] = None,
        router: Optional[LLMRouter] = None,
        metrics: Optional[RunMetrics] = None,
    ):
        self.config = config or load_config()
        self.router = router or LLMRouter(self.config)
        self.metrics = metrics if metrics is not None else RunMetrics()

    def complete(
        self,
        prompt: str,
        task_type: str,
        system_prompt: Optional[str] = None,
        response_model: Optional[Type[T]] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
    ) -> tuple[Any, str]:
        """
        Execute completion with automatic failover and optional JSON validation.
        
        Returns:
            tuple of (result, provider_name_used)
            Where result is either str or instance of response_model if response_model was provided.
        """
        chain = self.router.get_routing_chain(task_type)
        if not chain:
            raise LLMUnavailableError(
                task_type=task_type,
                chain_attempted=[],
                last_error="No active providers configured or API keys found in environment."
            )

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        last_error: Optional[str] = None
        failover_from: Optional[str] = None

        for idx, provider_name in enumerate(chain):
            provider = self.router.get_provider_instance(provider_name)
            if not provider:
                continue

            # Attempt provider execution with up to 2 exponential backoff retries
            p_cfg = self.config.providers.get(provider_name)
            max_retries = p_cfg.max_retries if p_cfg else 2

            for attempt in range(max_retries + 1):
                try:
                    logger.debug(
                        f"Attempting completion with provider '{provider_name}' (task='{task_type}', attempt={attempt + 1})"
                    )
                    res = provider.call_chat_completion(
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )
                    content = res["content"]
                    duration_ms = res["duration_ms"]

                    # If response_model is required, validate JSON output
                    if response_model is not None:
                        parsed, parse_err = parse_and_validate_json(content, target_schema=response_model)
                        if parse_err:
                            logger.warning(
                                f"Failed to parse structured JSON from {provider_name}: {parse_err}. Triggering 1 strict retry."
                            )
                            # Retry once with stricter JSON reminder prompt
                            retry_messages = list(messages) + [
                                {"role": "assistant", "content": content},
                                {"role": "user", "content": JSON_STRICT_RETRY_PROMPT},
                            ]
                            retry_res = provider.call_chat_completion(
                                messages=retry_messages,
                                temperature=0.1,
                                max_tokens=max_tokens,
                            )
                            parsed_retry, retry_err = parse_and_validate_json(
                                retry_res["content"], target_schema=response_model
                            )
                            if retry_err:
                                # Parsing still failed on this provider, escalate to next provider in fallback chain
                                raise ProviderError(
                                    f"Provider {provider_name} failed to produce valid schema: {retry_err}"
                                )
                            parsed = parsed_retry

                        # Record successful call metrics
                        self.metrics.record_call(
                            provider=provider_name,
                            model=provider.model,
                            task_type=task_type,
                            success=True,
                            duration_ms=duration_ms,
                            failover_from=failover_from,
                        )
                        return parsed, provider_name

                    # Plain text completion
                    self.metrics.record_call(
                        provider=provider_name,
                        model=provider.model,
                        task_type=task_type,
                        success=True,
                        duration_ms=duration_ms,
                        failover_from=failover_from,
                    )
                    return content, provider_name

                except ProviderError as err:
                    last_error = str(err)
                    # Retry on rate limit (429), 5xx, or timeout on the same provider
                    should_retry_same = (err.is_rate_limit or err.is_server_error or err.is_timeout) and (attempt < max_retries)
                    if should_retry_same:
                        backoff_delay = 1.5 * (2 ** attempt)
                        logger.warning(
                            f"Provider '{provider_name}' error ({err}). Retrying in {backoff_delay:.1f}s (attempt {attempt + 1}/{max_retries})..."
                        )
                        time.sleep(backoff_delay)
                        continue
                    else:
                        logger.warning(f"Provider '{provider_name}' failed after {attempt + 1} attempts: {err}")
                        break
                except Exception as ex:
                    last_error = str(ex)
                    logger.warning(f"Unexpected error with provider '{provider_name}': {ex}")
                    break

            # Record failed call for this provider
            self.metrics.record_call(
                provider=provider_name,
                model=provider.model,
                task_type=task_type,
                success=False,
                failover_from=failover_from,
                error=last_error,
            )

            # Check if there is another provider to failover to
            if idx + 1 < len(chain):
                next_provider = chain[idx + 1]
                logger.info(
                    f"Switching provider from '{provider_name}' to '{next_provider}' due to: {last_error}"
                )
                failover_from = provider_name

        # If loop completed without returning, all providers failed
        raise LLMUnavailableError(
            task_type=task_type,
            chain_attempted=chain,
            last_error=last_error,
        )
