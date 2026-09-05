"""
Pytest fixtures and configuration for Oasis backend test suite.
"""

from __future__ import annotations
import os
import sys
from pathlib import Path
from typing import Generator
import pytest
from starlette.testclient import TestClient

# Ensure backend package is in sys.path
backend_dir = str(Path(__file__).parent.parent.resolve())
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from oasis_backend.config import settings
from oasis_backend.database.connection import DatabaseManager, db_manager, get_db
from oasis_backend.database.repositories.user_repo import UserRepository
from oasis_backend.main import app
from oasis_backend.models.auth import GitHubUserPayload, UserRecord
from oasis_backend.services.auth_service import AuthService


@pytest.fixture(scope="session", autouse=True)
def setup_test_env(tmp_path_factory):
    """Configures isolated test environment paths."""
    test_db = tmp_path_factory.mktemp("oasis_db") / "test_oasis.db"
    test_ws = tmp_path_factory.mktemp("oasis_workspaces")
    
    settings.database_path = str(test_db)
    settings.workspaces_dir = str(test_ws)
    settings.jwt_secret_key = "test-secret-key-oasis-32-chars-long!"
    settings.encryption_key = ""
    settings.github_client_id = "test_client_id_123"
    settings.github_client_secret = "test_client_secret_456"
    settings.github_webhook_secret = "test-webhook-secret"

    # Initialize db schema
    db_manager.db_path = str(test_db)
    db_manager.init_db()


@pytest.fixture
def db_conn():
    with db_manager.get_connection() as conn:
        yield conn


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def test_user(db_conn) -> UserRecord:
    user_repo = UserRepository(db_conn)
    auth_service = AuthService(user_repo)
    
    gh_user = GitHubUserPayload(
        id=99999,
        login="oasis_tester",
        name="Oasis Tester",
        email="tester@oasis.dev",
        avatar_url="https://github.com/oasis_tester.png",
    )
    enc_token = auth_service.encrypt_token("ghp_mock_token_for_testing_12345")
    return user_repo.upsert_user(gh_user, enc_token)


@pytest.fixture
def auth_headers(test_user, db_conn) -> dict:
    user_repo = UserRepository(db_conn)
    auth_service = AuthService(user_repo)
    token = auth_service.create_jwt_token(test_user)
    return {"Authorization": f"Bearer {token}"}
