"""
Configuration management for the Oasis Backend.
"""

from __future__ import annotations
import base64
import hashlib
from pathlib import Path
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=[
            Path(__file__).resolve().parent.parent.parent / ".env",  # repo root
            Path(__file__).resolve().parent.parent / ".env",         # backend/.env
            ".env",
        ],
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Server
    port: int = 8000
    host: str = "0.0.0.0"
    debug: bool = False
    app_name: str = "Oasis Platform API"

    # Security & Tokens
    jwt_secret_key: str = "oasis-dev-insecure-secret-key-replace-in-production-12345"
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60 * 24  # 24 hours

    # 32-byte encryption key for Fernet at-rest OAuth token encryption
    encryption_key: str = ""

    # GitHub OAuth
    github_client_id: str = ""
    github_client_secret: str = ""
    github_redirect_uri: str = "http://localhost:3000/auth/callback"
    github_webhook_secret: str = ""
    github_oauth_scopes: str = "public_repo,read:user,user:email"

    # Storage paths
    database_path: str = ".oasis-agent/oasis_backend.db"
    workspaces_dir: str = ".oasis-workspaces"
    oasis_agent_config_path: str = "agent/oasis-agent.config.yaml"

    # Discovery & Workspace Cache
    discovery_cache_ttl_hours: int = 6
    workspace_idle_timeout_hours: int = 2

    # CORS
    cors_origins: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    def get_fernet_key(self) -> bytes:
        """
        Returns a valid 32-byte base64-encoded key for Fernet encryption.
        If not explicitly configured, derives one securely from jwt_secret_key.
        """
        if self.encryption_key and len(self.encryption_key.strip()) >= 32:
            try:
                raw = self.encryption_key.strip().encode("utf-8")
                # Test validity
                base64.urlsafe_b64decode(raw)
                return raw
            except Exception:
                pass
        # Deterministically derive 32-byte urlsafe base64 key from jwt_secret_key
        digest = hashlib.sha256(self.jwt_secret_key.encode("utf-8")).digest()
        return base64.urlsafe_b64encode(digest)

    def resolve_db_path(self) -> Path:
        p = Path(self.database_path)
        if not p.is_absolute():
            # Workspace root relative
            p = Path.cwd() / p
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def resolve_workspaces_dir(self) -> Path:
        p = Path(self.workspaces_dir)
        if not p.is_absolute():
            p = Path.cwd() / p
        p.mkdir(parents=True, exist_ok=True)
        return p


settings = Settings()
