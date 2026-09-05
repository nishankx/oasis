"""
Authentication and user models.
"""

from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class GitHubUserPayload(BaseModel):
    id: int
    login: str
    name: Optional[str] = None
    email: Optional[str] = None
    avatar_url: Optional[str] = None


class UserRecord(BaseModel):
    id: int
    github_id: int
    username: str
    name: Optional[str] = None
    email: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: str
    updated_at: str


class AuthCallbackRequest(BaseModel):
    code: str
    state: Optional[str] = None
    redirect_uri: Optional[str] = None


class AuthSessionResponse(BaseModel):
    authenticated: bool
    user: Optional[UserRecord] = None
    token: Optional[str] = None


class TokenPayload(BaseModel):
    sub: str  # user_id
    github_id: int
    username: str
    exp: int


class GitHubAuthUrlResponse(BaseModel):
    url: str
    state: str
