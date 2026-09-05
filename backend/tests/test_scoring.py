"""
Unit and integration tests for Scoring engine and leaderboard.
"""

from oasis_backend.database.repositories.pr_repo import PullRequestRepository
from oasis_backend.database.repositories.profile_repo import ProfileRepository
from oasis_backend.database.repositories.scoring_repo import ScoringRepository
from oasis_backend.models.profile import ExpertiseVector
from oasis_backend.services.scoring_service import ScoringService


def test_scoring_formula_calculation(db_conn):
    scoring_repo = ScoringRepository(db_conn)
    scoring_service = ScoringService(scoring_repo)

    base, conf_b, diff_b, repo_b, total, breakdown = scoring_service.calculate_score(
        gatekeeper_confidence=0.90,
        insertions=30,
        deletions=10,
        repo_stars=500,
    )

    assert base == 100
    assert conf_b == 45  # 0.90 * 50
    assert diff_b > 20   # ln(41) * 10 ~ 37
    assert repo_b > 20   # log10(501) * 12 ~ 32
    assert total == base + conf_b + diff_b + repo_b
    assert "Base Merged PR" in breakdown.explanation
    assert f"+{base}" in breakdown.explanation


def test_award_merged_pr_and_tier_promotion(db_conn, test_user):
    scoring_repo = ScoringRepository(db_conn)
    scoring_service = ScoringService(scoring_repo)
    pr_repo = PullRequestRepository(db_conn)
    profile_repo = ProfileRepository(db_conn)

    # Initialize user profile
    profile_repo.upsert_profile(
        test_user.id,
        ExpertiseVector(languages={"Python": 1.0}, topics={}, activity_level="medium", last_computed="2026-09-05T00:00:00Z"),
        cumulative_score=0,
    )

    # Create tracked PR
    pr_rec = pr_repo.create(
        pr_id="pr_test_score_1",
        workspace_id=None,
        user_id=test_user.id,
        repo_full_name="oasis/scoring-demo",
        pr_number=88,
        pr_url="https://github.com/oasis/scoring-demo/pull/88",
        head_branch="oasis-agent/fix-issue-88",
    )

    # Award score
    cnt = scoring_service.award_merged_pr(
        user_id=test_user.id,
        pr_id=pr_rec.pr_id,
        gatekeeper_confidence=0.95,
        insertions=20,
        deletions=5,
        repo_stars=200,
    )

    assert cnt.total_score >= 150
    assert cnt.user_id == test_user.id

    # Verify duplicate awards return existing
    cnt_dup = scoring_service.award_merged_pr(
        user_id=test_user.id,
        pr_id=pr_rec.pr_id,
    )
    assert cnt_dup.id == cnt.id

    # Verify user profile was updated
    updated_profile = profile_repo.get_profile(test_user.id)
    assert updated_profile is not None
    assert updated_profile.cumulative_score == cnt.total_score
    assert updated_profile.rank_tier != ""


def test_api_scoring_leaderboard_and_contributions(client, test_user, auth_headers):
    # Leaderboard
    lb_resp = client.get("/api/v1/scoring/leaderboard")
    assert lb_resp.status_code == 200
    entries = lb_resp.json()
    assert len(entries) >= 1
    assert any(e["username"] == test_user.username for e in entries)

    # Contributions me
    cnt_resp = client.get("/api/v1/scoring/contributions/me", headers=auth_headers)
    assert cnt_resp.status_code == 200
    assert isinstance(cnt_resp.json(), list)
