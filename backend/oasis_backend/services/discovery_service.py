"""
Discovery service: personalized repository & issue recommendation engine.
"""

from __future__ import annotations
import datetime
import math
from typing import Any, Dict, List, Optional
import httpx
from oasis_backend.config import settings
from oasis_backend.database.repositories.discovery_repo import DiscoveryRepository
from oasis_backend.models.discovery import CandidateRepo, DiscoveryResponse, IssueItem
from oasis_backend.models.profile import ExpertiseVector


class DiscoveryService:
    def __init__(self, discovery_repo: DiscoveryRepository):
        self.discovery_repo = discovery_repo

    async def get_recommended_repos(
        self,
        user_id: int,
        expertise: ExpertiseVector,
        github_token: Optional[str] = None,
        limit: int = 20,
        force_refresh: bool = False,
    ) -> DiscoveryResponse:
        """
        Returns cached recommendations if valid, or queries GitHub API and ranks candidate repositories.
        """
        if not force_refresh:
            cached = self.discovery_repo.get_cached(user_id)
            if cached:
                return cached

        # Fetch and rank fresh candidates
        candidates = await self._search_and_rank_candidates(expertise, github_token, limit=limit)

        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        expires = (
            datetime.datetime.now(datetime.timezone.utc)
            + datetime.timedelta(hours=settings.discovery_cache_ttl_hours)
        ).isoformat()

        # Cache in DB
        self.discovery_repo.set_cache(user_id, candidates, ttl_hours=settings.discovery_cache_ttl_hours)

        return DiscoveryResponse(
            repos=candidates,
            total=len(candidates),
            cached=False,
            cached_at=now,
            expires_at=expires,
        )

    async def search_repos(
        self,
        query: str,
        github_token: Optional[str] = None,
        limit: int = 15,
    ) -> List[CandidateRepo]:
        """
        Searches GitHub repositories directly by keyword, language, or exact 'owner/repo' format.
        Fetches an open issue for each repository if available.
        """
        clean_q = query.strip()
        if not clean_q:
            return []

        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Oasis-Platform",
        }
        if github_token:
            headers["Authorization"] = f"Bearer {github_token}"

        candidates: List[CandidateRepo] = []

        async with httpx.AsyncClient(timeout=20.0) as client:
            # Check if query is an exact repo format like 'owner/repo' or GitHub URL
            if "github.com/" in clean_q:
                clean_q = clean_q.split("github.com/")[-1].strip("/")
            
            parts = clean_q.split("/")
            if len(parts) == 2 and not any(ch in clean_q for ch in [" ", ":", ">", "<"]):
                # Direct single repo fetch
                owner, repo_name = parts[0], parts[1]
                try:
                    r_resp = await client.get(f"https://api.github.com/repos/{owner}/{repo_name}", headers=headers)
                    if r_resp.status_code == 200:
                        r_data = r_resp.json()
                        cand = await self._build_candidate_from_repo(client, r_data, headers)
                        if cand:
                            return [cand]
                except Exception:
                    pass

            # Search API query
            # If user didn't specify qualifier, search for active repos
            search_query = clean_q
            if "fork:" not in clean_q and "archived:" not in clean_q:
                search_query += " archived:false"

            try:
                resp = await client.get(
                    "https://api.github.com/search/repositories",
                    headers=headers,
                    params={
                        "q": search_query,
                        "sort": "stars",
                        "order": "desc",
                        "per_page": min(limit, 30),
                    },
                )
                if resp.status_code == 200:
                    items = resp.json().get("items", [])
                    for r_data in items:
                        cand = await self._build_candidate_from_repo(client, r_data, headers)
                        if cand:
                            candidates.append(cand)
            except Exception:
                pass

        return candidates

    async def _build_candidate_from_repo(
        self,
        client: httpx.AsyncClient,
        r_data: Dict[str, Any],
        headers: Dict[str, str],
    ) -> Optional[CandidateRepo]:
        """Fetches top good first issue or open issue for a repository and builds CandidateRepo."""
        owner = r_data["owner"]["login"]
        repo_name = r_data["name"]
        full_name = r_data["full_name"]

        issue_obj: Optional[IssueItem] = None
        if r_data.get("has_issues"):
            try:
                # First try finding good first issue / help wanted
                iss_resp = await client.get(
                    f"https://api.github.com/repos/{full_name}/issues",
                    headers=headers,
                    params={
                        "state": "open",
                        "labels": "good first issue,help wanted",
                        "per_page": 1,
                        "sort": "updated",
                    },
                )
                issues = iss_resp.json() if iss_resp.status_code == 200 and isinstance(iss_resp.json(), list) else []
                
                # Fallback to any open issue if no labeled ones
                if not issues:
                    iss_resp = await client.get(
                        f"https://api.github.com/repos/{full_name}/issues",
                        headers=headers,
                        params={"state": "open", "per_page": 1, "sort": "comments"},
                    )
                    issues = iss_resp.json() if iss_resp.status_code == 200 and isinstance(iss_resp.json(), list) else []

                # Filter out PRs returned by issues API
                for iss in issues:
                    if "pull_request" not in iss:
                        issue_labels = [
                            lbl.get("name") for lbl in iss.get("labels", []) if isinstance(lbl, dict)
                        ]
                        issue_obj = IssueItem(
                            number=iss["number"],
                            title=iss["title"],
                            body=iss.get("body") or "",
                            labels=issue_labels,
                            html_url=iss["html_url"],
                            comments_count=iss.get("comments", 0),
                            created_at=iss["created_at"],
                        )
                        break
            except Exception:
                pass

        reasons = [f"Found via GitHub repository search for '{repo_name}'"]
        if r_data.get("stargazers_count", 0) > 100:
            reasons.append(f"Popular project with {r_data.get('stargazers_count')} stars")

        return CandidateRepo(
            id=r_data["id"],
            name=r_data["name"],
            full_name=r_data["full_name"],
            owner=owner,
            html_url=r_data["html_url"],
            description=r_data.get("description") or "",
            language=r_data.get("language") or "Code",
            topics=r_data.get("topics", []),
            stars_count=r_data.get("stargazers_count", 0),
            forks_count=r_data.get("forks_count", 0),
            open_issues_count=r_data.get("open_issues_count", 0),
            pushed_at=r_data.get("pushed_at") or r_data.get("updated_at", ""),
            score=round(float(min(99.0, math.log10(max(10, r_data.get("stargazers_count", 0))) * 20.0)), 1),
            recommended_issue=issue_obj,
            score_reasons=reasons,
        )

    async def _search_and_rank_candidates(
        self,
        expertise: ExpertiseVector,
        github_token: Optional[str] = None,
        limit: int = 20,
    ) -> List[CandidateRepo]:
        """
        Queries GitHub Search API for open 'good first issue' / 'help wanted' issues matching
        the user's top languages and topics.
        """
        top_langs = sorted(expertise.languages.items(), key=lambda x: x[1], reverse=True)[:3]
        top_lang_names = [l[0] for l in top_langs] or ["Python", "TypeScript"]

        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Oasis-Platform",
        }
        if github_token:
            headers["Authorization"] = f"Bearer {github_token}"

        candidates: List[CandidateRepo] = []
        seen_repos = set()

        async with httpx.AsyncClient(timeout=20.0) as client:
            for lang in top_lang_names:
                # Query issues with good first issue or help wanted in target language
                query = f'state:open is:issue label:"good first issue","help wanted" language:{lang} archived:false'
                try:
                    resp = await client.get(
                        "https://api.github.com/search/issues",
                        headers=headers,
                        params={
                            "q": query,
                            "sort": "updated",
                            "order": "desc",
                            "per_page": 15,
                        },
                    )
                    if resp.status_code != 200:
                        continue
                    data = resp.json()
                    items = data.get("items", [])

                    for item in items:
                        # Extract repo URL and name: https://api.github.com/repos/owner/name
                        repo_api_url = item.get("repository_url")
                        if not repo_api_url:
                            continue
                        repo_full_name = "/".join(repo_api_url.split("/")[-2:])
                        if repo_full_name in seen_repos:
                            continue
                        seen_repos.add(repo_full_name)

                        # Fetch repo metadata
                        try:
                            r_resp = await client.get(repo_api_url, headers=headers)
                            if r_resp.status_code != 200:
                                continue
                            r_data = r_resp.json()

                            # Filter out archived or dormant repos (> 1 year no push)
                            if r_data.get("archived") or not r_data.get("has_issues"):
                                continue

                            # Parse issue
                            issue_labels = [lbl.get("name") for lbl in item.get("labels", []) if isinstance(lbl, dict)]
                            issue_obj = IssueItem(
                                number=item["number"],
                                title=item["title"],
                                body=item.get("body") or "",
                                labels=issue_labels,
                                html_url=item["html_url"],
                                comments_count=item.get("comments", 0),
                                created_at=item["created_at"],
                            )

                            # Compute composite score
                            score, reasons = self._calculate_composite_score(
                                repo_data=r_data,
                                issue=issue_obj,
                                expertise=expertise,
                            )

                            owner = r_data["owner"]["login"]
                            candidate = CandidateRepo(
                                id=r_data["id"],
                                name=r_data["name"],
                                full_name=r_data["full_name"],
                                owner=owner,
                                html_url=r_data["html_url"],
                                description=r_data.get("description") or "",
                                language=r_data.get("language") or lang,
                                topics=r_data.get("topics", []),
                                stars_count=r_data.get("stargazers_count", 0),
                                forks_count=r_data.get("forks_count", 0),
                                open_issues_count=r_data.get("open_issues_count", 0),
                                pushed_at=r_data.get("pushed_at") or r_data.get("updated_at", ""),
                                score=round(score, 2),
                                recommended_issue=issue_obj,
                                score_reasons=reasons,
                            )
                            candidates.append(candidate)
                        except Exception:
                            continue
                except Exception:
                    continue

        # Sort candidates by composite score descending
        candidates.sort(key=lambda c: c.score, reverse=True)
        return candidates[:limit]

    def _calculate_composite_score(
        self,
        repo_data: Dict[str, Any],
        issue: IssueItem,
        expertise: ExpertiseVector,
    ) -> tuple[float, List[str]]:
        """
        Calculates composite recommendation score based on:
        1. Language match weight (0-40 pts)
        2. Topic match weight (0-20 pts)
        3. Issue clarity & scope (0-25 pts)
        4. Repo health & activity (0-15 pts)
        """
        score = 0.0
        reasons: List[str] = []

        # 1. Language Match
        repo_lang = repo_data.get("language")
        lang_weight = expertise.languages.get(repo_lang, 0.0) if repo_lang else 0.0
        lang_points = lang_weight * 40.0
        if lang_points > 0:
            score += lang_points
            reasons.append(f"Strong match for primary language {repo_lang} (+{int(lang_points)} pts)")

        # 2. Topic Match
        repo_topics = [t.lower() for t in repo_data.get("topics", [])]
        matched_topics = [t for t in repo_topics if t in expertise.topics]
        topic_points = min(20.0, len(matched_topics) * 8.0)
        if topic_points > 0:
            score += topic_points
            reasons.append(f"Matched interested topics: {', '.join(matched_topics[:3])} (+{int(topic_points)} pts)")

        # 3. Issue Clarity & Scope
        issue_body = issue.body or ""
        clarity_points = 0.0
        # Well-scoped length (neither too brief nor massive)
        if 80 <= len(issue_body) <= 2500:
            clarity_points += 10.0
        # Contains reproduction/checklist markdown
        if "- [ ]" in issue_body or "- [x]" in issue_body or "###" in issue_body or "```" in issue_body:
            clarity_points += 10.0
        # Good first issue label
        if any("good first issue" in lbl.lower() or "help wanted" in lbl.lower() for lbl in issue.labels):
            clarity_points += 5.0
        score += clarity_points
        if clarity_points > 0:
            reasons.append(f"Well-scoped issue description and clear reproduction details (+{int(clarity_points)} pts)")

        # 4. Repo Health & Stars
        stars = repo_data.get("stargazers_count", 0)
        # Logarithmic scale for stars (sweet spot: 50 to 10,000 stars)
        star_points = min(10.0, math.log10(stars + 1) * 2.5) if stars > 10 else 2.0
        score += star_points
        reasons.append(f"Active repository with {stars} stars (+{int(star_points)} pts)")

        return score, reasons
