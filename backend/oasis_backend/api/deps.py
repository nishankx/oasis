"""
FastAPI dependency injection providers.
"""

from __future__ import annotations
import sqlite3
from typing import Generator, Optional
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from oasis_backend.database.connection import db_manager
from oasis_backend.database.repositories.discovery_repo import DiscoveryRepository
from oasis_backend.database.repositories.profile_repo import ProfileRepository
from oasis_backend.database.repositories.pr_repo import PullRequestRepository
from oasis_backend.database.repositories.scoring_repo import ScoringRepository
from oasis_backend.database.repositories.user_repo import UserRepository
from oasis_backend.database.repositories.workspace_repo import WorkspaceRepository
from oasis_backend.models.auth import UserRecord
from oasis_backend.services.agent_gateway import AgentGatewayService
from oasis_backend.services.auth_service import AuthService
from oasis_backend.services.discovery_service import DiscoveryService
from oasis_backend.services.profile_service import ProfileService
from oasis_backend.services.pr_service import PRService
from oasis_backend.services.scoring_service import ScoringService
from oasis_backend.services.workspace_service import WorkspaceService

security_scheme = HTTPBearer(auto_error=False)

# Singleton gateway service to reuse LLM client & cache
_agent_gateway_instance: Optional[AgentGatewayService] = None


def get_agent_gateway() -> AgentGatewayService:
    global _agent_gateway_instance
    if _agent_gateway_instance is None:
        _agent_gateway_instance = AgentGatewayService()
    return _agent_gateway_instance


def get_db() -> Generator[sqlite3.Connection, None, None]:
    with db_manager.get_connection() as conn:
        yield conn


def get_user_repo(conn: sqlite3.Connection = Depends(get_db)) -> UserRepository:
    return UserRepository(conn)


def get_profile_repo(conn: sqlite3.Connection = Depends(get_db)) -> ProfileRepository:
    return ProfileRepository(conn)


def get_discovery_repo(conn: sqlite3.Connection = Depends(get_db)) -> DiscoveryRepository:
    return DiscoveryRepository(conn)


def get_workspace_repo(conn: sqlite3.Connection = Depends(get_db)) -> WorkspaceRepository:
    return WorkspaceRepository(conn)


def get_pr_repo(conn: sqlite3.Connection = Depends(get_db)) -> PullRequestRepository:
    return PullRequestRepository(conn)


def get_scoring_repo(conn: sqlite3.Connection = Depends(get_db)) -> ScoringRepository:
    return ScoringRepository(conn)


def get_auth_service(user_repo: UserRepository = Depends(get_user_repo)) -> AuthService:
    return AuthService(user_repo)


def get_profile_service(profile_repo: ProfileRepository = Depends(get_profile_repo)) -> ProfileService:
    return ProfileService(profile_repo)


def get_workspace_service(
    workspace_repo: WorkspaceRepository = Depends(get_workspace_repo),
    agent_gateway: AgentGatewayService = Depends(get_agent_gateway),
) -> WorkspaceService:
    return WorkspaceService(workspace_repo, agent_gateway)


def get_discovery_service(
    discovery_repo: DiscoveryRepository = Depends(get_discovery_repo),
) -> DiscoveryService:
    return DiscoveryService(discovery_repo)


def get_scoring_service(
    scoring_repo: ScoringRepository = Depends(get_scoring_repo),
) -> ScoringService:
    return ScoringService(scoring_repo)


def get_pr_service(
    pr_repo: PullRequestRepository = Depends(get_pr_repo),
    workspace_service: WorkspaceService = Depends(get_workspace_service),
    agent_gateway: AgentGatewayService = Depends(get_agent_gateway),
    auth_service: AuthService = Depends(get_auth_service),
    scoring_service: ScoringService = Depends(get_scoring_service),
) -> PRService:
    return PRService(pr_repo, workspace_service, agent_gateway, auth_service, scoring_service)


async def get_current_user(
    auth: Optional[HTTPAuthorizationCredentials] = Security(security_scheme),
    auth_service: AuthService = Depends(get_auth_service),
    user_repo: UserRepository = Depends(get_user_repo),
) -> UserRecord:
    """Dependency that ensures request has a valid Bearer JWT and returns the user."""
    if not auth or not auth.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide a valid Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = auth_service.verify_jwt_token(auth.credentials)
        user = user_repo.get_by_id(int(payload.sub))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account no longer exists.",
            )
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_optional_user(
    auth: Optional[HTTPAuthorizationCredentials] = Security(security_scheme),
    auth_service: AuthService = Depends(get_auth_service),
    user_repo: UserRepository = Depends(get_user_repo),
) -> Optional[UserRecord]:
    """Optional user dependency for endpoints accessible both publicly and authenticated."""
    if not auth or not auth.credentials:
        return None
    try:
        payload = auth_service.verify_jwt_token(auth.credentials)
        return user_repo.get_by_id(int(payload.sub))
    except Exception:
        return None
