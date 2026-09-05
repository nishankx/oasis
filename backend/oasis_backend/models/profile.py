"""
User profile and expertise models.
"""

from __future__ import annotations
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class ExpertiseVector(BaseModel):
    languages: Dict[str, float] = Field(default_factory=dict)
    topics: Dict[str, float] = Field(default_factory=dict)
    activity_level: str = "medium"  # high, medium, low
    last_computed: str


class ProfileRecord(BaseModel):
    user_id: int
    expertise: ExpertiseVector
    cumulative_score: int = 0
    rank_tier: str = "Novice Contributor"


class ProfileSnapshotRecord(BaseModel):
    id: int
    user_id: int
    expertise: ExpertiseVector
    cumulative_score: int
    snapshot_timestamp: str


class PublicUserProfile(BaseModel):
    username: str
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    cumulative_score: int
    rank_tier: str
    expertise: ExpertiseVector
    recent_contributions_count: int = 0
