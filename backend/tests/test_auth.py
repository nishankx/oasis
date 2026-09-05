"""
Unit and integration tests for Authentication and OAuth.
"""

import pytest
from unittest.mock import AsyncMock, patch
from oasis_backend.database.repositories.user_repo import UserRepository
from oasis_backend.models.auth import GitHubUserPayload
from oasis_backend.services.auth_service import AuthService


def test_token_encryption_and_decryption(db_conn):
    user_repo = UserRepository(db_conn)
    auth_service = AuthService(user_repo)

    original_token = "ghp_secret_access_token_abc123"
    encrypted = auth_service.encrypt_token(original_token)
    assert encrypted != original_token
    
    decrypted = auth_service.decrypt_token(encrypted)
    assert decrypted == original_token


def test_jwt_token_creation_and_verification(test_user, db_conn):
    user_repo = UserRepository(db_conn)
    auth_service = AuthService(user_repo)

    jwt_token = auth_service.create_jwt_token(test_user)
    assert isinstance(jwt_token, str) and len(jwt_token) > 20

    payload = auth_service.verify_jwt_token(jwt_token)
    assert payload.sub == str(test_user.id)
    assert payload.username == test_user.username
    assert payload.github_id == test_user.github_id


def test_jwt_token_invalid_signature(db_conn):
    user_repo = UserRepository(db_conn)
    auth_service = AuthService(user_repo)

    with pytest.raises(ValueError):
        auth_service.verify_jwt_token("invalid.jwt.token")


def test_api_auth_github_url(client):
    response = client.get("/api/v1/auth/github/url")
    assert response.status_code == 200
    data = response.json()
    assert "github.com/login/oauth/authorize" in data["url"]
    assert "client_id=" in data["url"]
    assert len(data["state"]) > 10


def test_api_auth_session_unauthenticated(client):
    response = client.get("/api/v1/auth/session")
    assert response.status_code == 200
    data = response.json()
    assert data["authenticated"] is False
    assert data["user"] is None


def test_api_auth_session_authenticated(client, test_user, auth_headers):
    response = client.get("/api/v1/auth/session", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["authenticated"] is True
    assert data["user"]["username"] == test_user.username
    assert data["user"]["id"] == test_user.id


def test_api_auth_github_callback(client):
    import asyncio

    async def _run():
        mock_gh_user = GitHubUserPayload(
            id=77777,
            login="new_contributor",
            name="New Contributor",
            email="new@contributor.org",
            avatar_url="https://github.com/new.png",
        )

        with patch.object(AuthService, "exchange_code_for_token", new_callable=AsyncMock) as mock_exchange, \
             patch.object(AuthService, "fetch_github_user", new_callable=AsyncMock) as mock_fetch:
            mock_exchange.return_value = "ghp_mock_token_77777"
            mock_fetch.return_value = mock_gh_user

            response = client.post("/api/v1/auth/github/callback", json={"code": "sample_auth_code_123"})
            assert response.status_code == 200
            data = response.json()
            assert data["authenticated"] is True
            assert data["user"]["username"] == "new_contributor"
            assert len(data["token"]) > 20

    asyncio.run(_run())
