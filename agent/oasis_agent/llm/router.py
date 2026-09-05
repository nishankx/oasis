"""
Dynamic task-to-provider routing, health checks, and fallback chain resolution.
"""

import logging
import time
from typing import Dict, List, Optional
from oasis_agent.config import OasisConfig, ProviderConfig, TaskRouting
from oasis_agent.llm.providers import OpenAICompatibleProvider, ProviderError

logger = logging.getLogger("oasis_agent.router")


class LLMRouter:
    """Manages provider instances, checks availability, and resolves fallback chains."""

    def __init__(self, config: OasisConfig):
        self.config = config
        self._provider_instances: Dict[str, OpenAICompatibleProvider] = {}
        self._initialize_providers()

    def _initialize_providers(self):
        """Instantiate low-level provider adapters for configured entries."""
        for name, p_cfg in self.config.providers.items():
            api_key = p_cfg.get_api_key()
            if api_key:
                self._provider_instances[name] = OpenAICompatibleProvider(
                    name=name,
                    base_url=p_cfg.base_url,
                    model=p_cfg.model,
                    api_key=api_key,
                    timeout_seconds=p_cfg.timeout_seconds,
                )

    def get_provider_instance(self, name: str) -> Optional[OpenAICompatibleProvider]:
        return self._provider_instances.get(name)

    def register_custom_provider(self, name: str, provider: OpenAICompatibleProvider):
        """Allows registering mock or custom providers (useful for testing)."""
        self._provider_instances[name] = provider

    def get_routing_chain(self, task_type: str) -> List[str]:
        """
        Return the list of provider names configured for a task_type [primary, *fallbacks].
        Filters out providers that do not have an API key available in the environment.
        """
        routing: Optional[TaskRouting] = self.config.llm_routing.get(task_type)
        if not routing:
            # Fallback to whatever provider is available
            candidates = list(self.config.providers.keys())
        else:
            candidates = [routing.primary] + [f for f in routing.fallback if f != routing.primary]

        # Filter to only providers with configured keys / active instances
        active_chain = [name for name in candidates if name in self._provider_instances]

        if not active_chain and candidates:
            missing_envs = [
                self.config.providers[c].api_key_env
                for c in candidates
                if c in self.config.providers
            ]
            logger.warning(
                f"No active providers available for task '{task_type}'. Missing env vars: {missing_envs}"
            )

        return active_chain

    def check_provider_health(self, name: str) -> Dict[str, any]:
        """Execute a minimal ping call to verify provider reachability and latency."""
        p_cfg = self.config.providers.get(name)
        if not p_cfg:
            return {"configured": False, "reachable": False, "status": "Not configured in YAML"}

        api_key = p_cfg.get_api_key()
        if not api_key:
            return {
                "configured": False,
                "reachable": False,
                "status": f"Missing env var: {p_cfg.api_key_env}",
            }

        instance = self._provider_instances.get(name)
        if not instance:
            instance = OpenAICompatibleProvider(
                name=name,
                base_url=p_cfg.base_url,
                model=p_cfg.model,
                api_key=api_key,
                timeout_seconds=15,
            )

        start = time.perf_counter()
        try:
            # Minimal completion test
            res = instance.call_chat_completion(
                messages=[{"role": "user", "content": "Respond with OK"}],
                max_tokens=5,
            )
            latency_ms = int((time.perf_counter() - start) * 1000)
            return {
                "configured": True,
                "reachable": True,
                "latency_ms": latency_ms,
                "model": p_cfg.model,
                "status": "Operational",
            }
        except ProviderError as e:
            latency_ms = int((time.perf_counter() - start) * 1000)
            status_text = "Rate limited (429)" if e.is_rate_limit else str(e)
            return {
                "configured": True,
                "reachable": False,
                "latency_ms": latency_ms,
                "model": p_cfg.model,
                "status": status_text,
            }
        except Exception as e:
            latency_ms = int((time.perf_counter() - start) * 1000)
            return {
                "configured": True,
                "reachable": False,
                "latency_ms": latency_ms,
                "model": p_cfg.model,
                "status": f"Error: {e}",
            }
