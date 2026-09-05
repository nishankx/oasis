"""
Discovery and repository recommendation models.
"""

from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field


class IssueItem(BaseModel):
    number: int
    title: str
    body: Optional[str] = ""
    labels: List[str] = Field(default_factory=list)
    html_url: str
    comments_count: int = 0
    created_at: str


class CandidateRepo(BaseModel):
    id: int
    name: str
    full_name: str
    owner: str
    html_url: str
    description: Optional[str] = ""
    language: Optional[str] = ""
    topics: List[str] = Field(default_factory=list)
    stars_count: int = 0
    forks_count: int = 0
    open_issues_count: int = 0
    pushed_at: str
    score: float = 0.0
    recommended_issue: Optional[IssueItem] = None
    score_reasons: List[str] = Field(default_factory=list)


class DiscoveryResponse(BaseModel):
    repos: List[CandidateRepo]
    total: int
    cached: bool = False
    cached_at: Optional[str] = None
    expires_at: Optional[str] = None
