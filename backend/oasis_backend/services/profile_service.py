"""
Profile analysis service: builds and maintains the developer's tech-expertise graph.
"""

from __future__ import annotations
import collections
import datetime
from typing import Any, Dict, List, Optional
import httpx
from oasis_backend.database.repositories.profile_repo import ProfileRepository
from oasis_backend.models.profile import ExpertiseVector, ProfileRecord, PublicUserProfile


class ProfileService:
    def __init__(self, profile_repo: ProfileRepository):
        self.profile_repo = profile_repo

    async def build_or_refresh_profile(
        self,
        user_id: int,
        username: str,
        github_token: Optional[str] = None,
    ) -> ProfileRecord:
        """
        Fetches repositories, starred repos, activity events, and pinned items from GitHub,
        computes a weighted expertise vector, and saves versioned snapshots.
        """
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # If no token provided or in offline/mock mode, generate sensible baseline
        if not github_token:
            existing = self.profile_repo.get_profile(user_id)
            if existing:
                return existing
            baseline_vector = ExpertiseVector(
                languages={"Python": 0.5, "TypeScript": 0.3, "Rust": 0.2},
                topics={"cli": 0.4, "web": 0.3, "api": 0.3},
                activity_level="medium",
                last_computed=now,
            )
            return self.profile_repo.upsert_profile(user_id, baseline_vector)

        headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Oasis-Platform",
        }

        lang_counts: collections.Counter[str] = collections.Counter()
        topic_counts: collections.Counter[str] = collections.Counter()
        event_count = 0

        async with httpx.AsyncClient(timeout=20.0) as client:
            # 1. Fetch user's owned repositories (up to 30 most recently updated)
            try:
                repos_resp = await client.get(
                    f"https://api.github.com/users/{username}/repos?sort=updated&per_page=30&type=owner",
                    headers=headers,
                )
                if repos_resp.status_code == 200:
                    repos_data = repos_resp.json()
                    for repo in repos_data:
                        if repo.get("fork"):
                            continue
                        lang = repo.get("language")
                        if lang:
                            lang_counts[lang] += 3  # Higher weight for owned repos
                        for topic in repo.get("topics", []):
                            topic_counts[topic.lower()] += 2
            except Exception:
                pass

            # 2. Fetch user's starred repositories (up to 30)
            try:
                starred_resp = await client.get(
                    f"https://api.github.com/users/{username}/starred?per_page=30",
                    headers=headers,
                )
                if starred_resp.status_code == 200:
                    starred_data = starred_resp.json()
                    for repo in starred_data:
                        lang = repo.get("language")
                        if lang:
                            lang_counts[lang] += 1  # Weight for interest
                        for topic in repo.get("topics", []):
                            topic_counts[topic.lower()] += 1
            except Exception:
                pass

            # 3. Fetch recent events to gauge activity level
            try:
                events_resp = await client.get(
                    f"https://api.github.com/users/{username}/events?per_page=30",
                    headers=headers,
                )
                if events_resp.status_code == 200:
                    events_data = events_resp.json()
                    event_count = len(events_data)
            except Exception:
                pass

            # 4. Fetch pinned repositories via GraphQL if token has permissions
            try:
                gql_query = """
                query($login: String!) {
                    user(login: $login) {
                        pinnedItems(first: 6, types: REPOSITORY) {
                            nodes {
                                ... on Repository {
                                    primaryLanguage { name }
                                    repositoryTopics(first: 5) {
                                        nodes { topic { name } }
                                    }
                                }
                            }
                        }
                    }
                }
                """
                gql_resp = await client.post(
                    "https://api.github.com/graphql",
                    headers=headers,
                    json={"query": gql_query, "variables": {"login": username}},
                )
                if gql_resp.status_code == 200:
                    gql_data = gql_resp.json()
                    pinned_nodes = (
                        gql_data.get("data", {})
                        .get("user", {})
                        .get("pinnedItems", {})
                        .get("nodes", [])
                    )
                    for p in pinned_nodes:
                        prim_lang = p.get("primaryLanguage")
                        if prim_lang and prim_lang.get("name"):
                            lang_counts[prim_lang["name"]] += 5  # Strongest signal
                        for top in p.get("repositoryTopics", {}).get("nodes", []):
                            t_name = top.get("topic", {}).get("name")
                            if t_name:
                                topic_counts[t_name.lower()] += 3
            except Exception:
                pass

        # Normalize language weights
        total_lang_weight = sum(lang_counts.values()) or 1
        normalized_languages = {
            lang: round(cnt / total_lang_weight, 3)
            for lang, cnt in lang_counts.most_common(8)
        }

        # Normalize topic weights
        total_topic_weight = sum(topic_counts.values()) or 1
        normalized_topics = {
            topic: round(cnt / total_topic_weight, 3)
            for topic, cnt in topic_counts.most_common(10)
        }

        # Fallback if empty profile
        if not normalized_languages:
            normalized_languages = {"Python": 0.6, "TypeScript": 0.4}

        # Determine activity level
        if event_count >= 20:
            activity_level = "high"
        elif event_count >= 5:
            activity_level = "medium"
        else:
            activity_level = "low"

        vector = ExpertiseVector(
            languages=normalized_languages,
            topics=normalized_topics,
            activity_level=activity_level,
            last_computed=now,
        )

        return self.profile_repo.upsert_profile(user_id, vector)

    def get_profile(self, user_id: int) -> Optional[ProfileRecord]:
        return self.profile_repo.get_profile(user_id)
