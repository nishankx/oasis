"""
Unit and integration tests for Profile analysis and expertise graph.
"""

import pytest
from oasis_backend.database.repositories.profile_repo import ProfileRepository
from oasis_backend.models.profile import ExpertiseVector
from oasis_backend.services.profile_service import ProfileService


def test_build_baseline_profile(db_conn):
    import asyncio
    from oasis_backend.database.repositories.user_repo import UserRepository
    from oasis_backend.models.auth import GitHubUserPayload

    async def _run():
        user_repo = UserRepository(db_conn)
        fresh_user = user_repo.upsert_user(
            GitHubUserPayload(id=88888, login="fresh_coder", name="Fresh Coder", email="fresh@coder.dev"),
            "mock_enc_token",
        )
        profile_repo = ProfileRepository(db_conn)
        profile_service = ProfileService(profile_repo)

        profile = await profile_service.build_or_refresh_profile(fresh_user.id, fresh_user.username, github_token=None)
        assert profile.user_id == fresh_user.id
        assert "Python" in profile.expertise.languages
        assert profile.cumulative_score == 0
        assert profile.rank_tier == "Novice Contributor"

    asyncio.run(_run())


def test_profile_snapshots(test_user, db_conn):
    import asyncio

    async def _run():
        profile_repo = ProfileRepository(db_conn)
        profile_service = ProfileService(profile_repo)

        await profile_service.build_or_refresh_profile(test_user.id, test_user.username, github_token=None)
        snapshots = profile_repo.get_snapshots(test_user.id)
        assert len(snapshots) >= 1
        assert snapshots[0].user_id == test_user.id

    asyncio.run(_run())


def test_api_get_my_profile(client, test_user, auth_headers):
    response = client.get("/api/v1/profile/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == test_user.id
    assert "languages" in data["expertise"]


def test_api_refresh_my_profile(client, test_user, auth_headers):
    response = client.post("/api/v1/profile/refresh", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == test_user.id


def test_api_get_public_profile(client, test_user):
    response = client.get(f"/api/v1/profile/{test_user.username}")
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == test_user.username
    assert "expertise" in data
    assert "cumulative_score" in data


def test_api_get_public_profile_not_found(client):
    response = client.get("/api/v1/profile/non_existent_developer_12345")
    assert response.status_code == 404
