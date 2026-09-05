"""
Unit and integration tests for repository and issue discovery.
"""

from unittest.mock import AsyncMock, patch
import pytest
from oasis_backend.database.repositories.discovery_repo import DiscoveryRepository
from oasis_backend.models.discovery import CandidateRepo, IssueItem
from oasis_backend.models.profile import ExpertiseVector
from oasis_backend.services.discovery_service import DiscoveryService


def test_calculate_composite_score(db_conn):
    discovery_repo = DiscoveryRepository(db_conn)
    discovery_service = DiscoveryService(discovery_repo)

    expertise = ExpertiseVector(
        languages={"Python": 0.6, "TypeScript": 0.4},
        topics={"fastapi": 0.5, "cli": 0.5},
        activity_level="high",
        last_computed="2026-09-05T12:00:00Z",
    )

    repo_data = {
        "language": "Python",
        "topics": ["fastapi", "web"],
        "stargazers_count": 250,
    }

    issue = IssueItem(
        number=42,
        title="Fix pagination cursor in API",
        body="### Description\nWhen requesting the second page, the cursor offset is invalid.\n- [ ] Add unit test\n- [ ] Fix offset",
        labels=["good first issue", "bug"],
        html_url="https://github.com/oasis/example/issues/42",
        created_at="2026-09-01T00:00:00Z",
    )

    score, reasons = discovery_service._calculate_composite_score(repo_data, issue, expertise)
    assert score > 30.0
    assert any("Python" in r for r in reasons)
    assert any("good-scoped" in r.lower() or "reproduction" in r.lower() for r in reasons)


def test_discovery_caching(db_conn, test_user):
    import asyncio

    async def _run():
        discovery_repo = DiscoveryRepository(db_conn)
        discovery_service = DiscoveryService(discovery_repo)

        expertise = ExpertiseVector(
            languages={"Python": 0.8},
            topics={"cli": 0.5},
            activity_level="medium",
            last_computed="2026-09-05T12:00:00Z",
        )

        mock_candidates = [
            CandidateRepo(
                id=101,
                name="awesome-cli",
                full_name="org/awesome-cli",
                owner="org",
                html_url="https://github.com/org/awesome-cli",
                description="An awesome CLI tool",
                language="Python",
                topics=["cli"],
                stars_count=500,
                pushed_at="2026-09-04T00:00:00Z",
                score=78.5,
            )
        ]

        with patch.object(discovery_service, "_search_and_rank_candidates", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = mock_candidates

            # 1. Fresh call queries search
            res1 = await discovery_service.get_recommended_repos(test_user.id, expertise, limit=10)
            assert res1.cached is False
            assert len(res1.repos) == 1
            assert mock_search.call_count == 1

            # 2. Subsequent call returns from cache
            res2 = await discovery_service.get_recommended_repos(test_user.id, expertise, limit=10)
            assert res2.cached is True
            assert len(res2.repos) == 1
            assert mock_search.call_count == 1  # Not called again!

            # 3. Force refresh re-queries
            res3 = await discovery_service.get_recommended_repos(test_user.id, expertise, limit=10, force_refresh=True)
            assert res3.cached is False
            assert mock_search.call_count == 2

    asyncio.run(_run())


def test_api_discovery_repos(client, auth_headers):
    mock_candidates = [
        CandidateRepo(
            id=202,
            name="oasis-demo-repo",
            full_name="oasis/demo",
            owner="oasis",
            html_url="https://github.com/oasis/demo",
            description="Demo repo",
            language="Python",
            topics=["cli"],
            stars_count=120,
            pushed_at="2026-09-05T00:00:00Z",
            score=65.0,
        )
    ]

    with patch.object(DiscoveryService, "_search_and_rank_candidates", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = mock_candidates
        # Calling refresh forces recalculation bypassing any prior cache
        response = client.post("/api/v1/discovery/refresh", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["repos"]) == 1
        assert data["repos"][0]["name"] == "oasis-demo-repo"
