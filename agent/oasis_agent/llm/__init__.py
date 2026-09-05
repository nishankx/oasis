"""
LLM Client and Provider Failover Subsystem for oasis-agent.
"""

from .client import LLMClient, LLMUnavailableError
from .router import LLMRouter

__all__ = ["LLMClient", "LLMUnavailableError", "LLMRouter"]
