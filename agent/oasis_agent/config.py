"""
Configuration loader and settings manager for oasis-agent.
Loads settings from oasis-agent.config.yaml and environment variables (.env).
"""

import os
from pathlib import Path
from typing import Dict, List, Optional
import yaml
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load .env from current directory, package directory, and ~/.oasis-agent/
load_dotenv()
pkg_env = Path(__file__).resolve().parent.parent / ".env"
if pkg_env.exists():
    load_dotenv(pkg_env)
home_env = Path.home() / ".oasis-agent" / ".env"
if home_env.exists():
    load_dotenv(home_env)


class ProviderConfig(BaseModel):
    base_url: str
    model: str
    api_key_env: str
    timeout_seconds: int = 35
    max_retries: int = 2

    def get_api_key(self) -> Optional[str]:
        return os.environ.get(self.api_key_env)

    def is_available(self) -> bool:
        key = self.get_api_key()
        return bool(key and key.strip())


class TaskRouting(BaseModel):
    primary: str
    fallback: List[str] = Field(default_factory=list)


class GatekeeperConfig(BaseModel):
    confidence_threshold: float = 0.70
    run_local_tests: bool = True
    reject_on_test_failure: bool = True
    reject_on_empty_diff: bool = True
    reject_on_whitespace_only: bool = True
    reject_on_comment_only: bool = True


class GitConfig(BaseModel):
    branch_prefix: str = "oasis-agent/fix-issue-"
    commit_message_prefix: str = "fix"
    shallow_clone: bool = True
    cache_dir: str = ".oasis-agent/cache"


class ReportingConfig(BaseModel):
    output_dir: str = ".oasis-agent/reports"
    database_path: str = ".oasis-agent/history.db"
    comment_on_rejection: bool = False
    clean_workspace_on_success: bool = True


class PrivacyConfig(BaseModel):
    warning_dismissed: bool = False


class OasisConfig(BaseModel):
    version: str = "1.0"
    providers: Dict[str, ProviderConfig] = Field(default_factory=dict)
    llm_routing: Dict[str, TaskRouting] = Field(default_factory=dict)
    gatekeeper: GatekeeperConfig = Field(default_factory=GatekeeperConfig)
    git: GitConfig = Field(default_factory=GitConfig)
    reporting: ReportingConfig = Field(default_factory=ReportingConfig)
    privacy: PrivacyConfig = Field(default_factory=PrivacyConfig)


def find_config_file(custom_path: Optional[str] = None) -> Optional[Path]:
    """Locate oasis-agent.config.yaml in custom path, current dir, or parent dirs."""
    if custom_path:
        p = Path(custom_path)
        if p.exists():
            return p
    current = Path.cwd()
    candidate = current / "oasis-agent.config.yaml"
    if candidate.exists():
        return candidate
    for parent in current.parents:
        candidate = parent / "oasis-agent.config.yaml"
        if candidate.exists():
            return candidate
    # Check user home directory ~/.oasis-agent/oasis-agent.config.yaml
    home_candidate = Path.home() / ".oasis-agent" / "oasis-agent.config.yaml"
    if home_candidate.exists():
        return home_candidate

    # Check package root directory (e.g. agent/ directory)
    pkg_candidate = Path(__file__).resolve().parent.parent / "oasis-agent.config.yaml"
    if pkg_candidate.exists():
        return pkg_candidate

    # Check monorepo root directory
    root_candidate = Path(__file__).resolve().parent.parent.parent / "oasis-agent.config.yaml"
    if root_candidate.exists():
        return root_candidate

    return None


def load_config(config_path: Optional[str] = None) -> OasisConfig:
    """Load configuration from YAML file or return defaults."""
    path = find_config_file(config_path)
    if path and path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            return OasisConfig.model_validate(data)
        except Exception as e:
            # Fallback to default if corrupted
            print(f"[Warning] Failed to parse config from {path}: {e}. Using defaults.")
    
    # Return minimal default configuration matching active free-tier models
    return OasisConfig(
        providers={
            "google_gemini_flash": ProviderConfig(
                base_url="https://generativelanguage.googleapis.com/v1beta/openai",
                model="gemini-flash-latest",
                api_key_env="GOOGLE_API_KEY",
            ),
            "groq_gpt_oss": ProviderConfig(
                base_url="https://api.groq.com/openai/v1",
                model="openai/gpt-oss-120b",
                api_key_env="GROQ_API_KEY",
            ),
            "groq_qwen": ProviderConfig(
                base_url="https://api.groq.com/openai/v1",
                model="qwen/qwen3.8-27b",
                api_key_env="GROQ_API_KEY",
            ),
            "openrouter_nemotron": ProviderConfig(
                base_url="https://openrouter.ai/api/v1",
                model="nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
                api_key_env="OPENROUTER_API_KEY",
            ),
            "nvidia_nim": ProviderConfig(
                base_url="https://integrate.api.nvidia.com/v1",
                model="meta/llama-3.2-11b-vision-instruct",
                api_key_env="NVIDIA_API_KEY",
            ),
        },
        llm_routing={
            "context_mapping": TaskRouting(primary="groq_gpt_oss", fallback=["google_gemini_flash", "nvidia_nim"]),
            "codebase_search": TaskRouting(primary="groq_gpt_oss", fallback=["groq_qwen", "google_gemini_flash"]),
            "code_editing": TaskRouting(primary="groq_gpt_oss", fallback=["google_gemini_flash", "openrouter_nemotron", "nvidia_nim"]),
            "meaningfulness_judgment": TaskRouting(primary="groq_gpt_oss", fallback=["google_gemini_flash", "openrouter_nemotron", "nvidia_nim"]),
            "pr_description_generation": TaskRouting(primary="groq_gpt_oss", fallback=["google_gemini_flash"]),
            "review_report_generation": TaskRouting(primary="groq_gpt_oss", fallback=["google_gemini_flash"]),
        }
    )


def save_config(config: OasisConfig, config_path: Optional[str] = None):
    """Save configuration back to YAML file."""
    path = find_config_file(config_path) or Path("oasis-agent.config.yaml")
    data = config.model_dump(mode="json")
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False)
