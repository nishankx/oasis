"""
Authentication service: GitHub OAuth 2.0, Fernet token encryption at rest, and JWT sessions.
"""

from __future__ import annotations
import datetime
import secrets
from typing import Optional, Tuple
from cryptography.fernet import Fernet
import httpx
import jwt
from oasis_backend.config import settings
from oasis_backend.database.repositories.user_repo import UserRepository
from oasis_backend.models.auth import GitHubAuthUrlResponse, GitHubUserPayload, TokenPayload, UserRecord


class AuthService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo
        self.fernet = Fernet(settings.get_fernet_key())

    def encrypt_token(self, plain_token: str) -> str:
        """Encrypts an access token using Fernet AES encryption."""
        return self.fernet.encrypt(plain_token.encode("utf-8")).decode("utf-8")

    def decrypt_token(self, encrypted_token: str) -> str:
        """Decrypts a stored access token."""
        return self.fernet.decrypt(encrypted_token.encode("utf-8")).decode("utf-8")

    def get_decrypted_user_token(self, user_id: int) -> Optional[str]:
        """Retrieves and decrypts the user's GitHub OAuth token."""
        enc = self.user_repo.get_encrypted_token(user_id)
        if not enc:
            return None
        try:
            return self.decrypt_token(enc)
        except Exception:
            return None

    def generate_oauth_url(self, redirect_uri: Optional[str] = None) -> GitHubAuthUrlResponse:
        """Generates GitHub OAuth authorization URL."""
        if not settings.github_client_id:
            raise ValueError(
                "GITHUB_CLIENT_ID is not configured. Please set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET in backend/.env"
            )

        state = secrets.token_urlsafe(16)
        callback = redirect_uri or settings.github_redirect_uri
        scope = settings.github_oauth_scopes

        url = (
            f"https://github.com/login/oauth/authorize"
            f"?client_id={settings.github_client_id}"
            f"&redirect_uri={callback}"
            f"&scope={scope}"
            f"&state={state}"
        )
        return GitHubAuthUrlResponse(url=url, state=state)

    async def exchange_code_for_token(self, code: str, redirect_uri: Optional[str] = None) -> str:
        """Exchanges authorization code for GitHub access token."""
        callback = redirect_uri or settings.github_redirect_uri
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://github.com/login/oauth/access_token",
                headers={"Accept": "application/json"},
                data={
                    "client_id": settings.github_client_id,
                    "client_secret": settings.github_client_secret,
                    "code": code,
                    "redirect_uri": callback,
                },
            )
            if resp.status_code != 200:
                raise RuntimeError(f"GitHub token exchange failed: {resp.text}")
            data = resp.json()
            if "error" in data:
                raise RuntimeError(f"GitHub OAuth error: {data.get('error_description', data['error'])}")
            token = data.get("access_token")
            if not token:
                raise RuntimeError("No access_token returned by GitHub.")
            return token

    async def fetch_github_user(self, access_token: str) -> GitHubUserPayload:
        """Fetches user details and verified email from GitHub API."""
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Oasis-Platform",
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            user_resp = await client.get("https://api.github.com/user", headers=headers)
            if user_resp.status_code != 200:
                raise RuntimeError(f"Failed to fetch user profile: {user_resp.text}")
            user_data = user_resp.json()

            email = user_data.get("email")
            if not email:
                # Try fetching emails endpoint
                try:
                    email_resp = await client.get("https://api.github.com/user/emails", headers=headers)
                    if email_resp.status_code == 200:
                        emails = email_resp.json()
                        primary = next((e["email"] for e in emails if e.get("primary")), None)
                        email = primary or (emails[0]["email"] if emails else None)
                except Exception:
                    pass

            return GitHubUserPayload(
                id=user_data["id"],
                login=user_data["login"],
                name=user_data.get("name"),
                email=email,
                avatar_url=user_data.get("avatar_url"),
            )

    def create_jwt_token(self, user: UserRecord) -> str:
        """Issues a signed JWT session token."""
        exp = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
            minutes=settings.jwt_expiration_minutes
        )
        payload = {
            "sub": str(user.id),
            "github_id": user.github_id,
            "username": user.username,
            "exp": int(exp.timestamp()),
        }
        return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

    def verify_jwt_token(self, token: str) -> TokenPayload:
        """Validates and decodes JWT session token."""
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
            )
            return TokenPayload(
                sub=payload["sub"],
                github_id=payload["github_id"],
                username=payload["username"],
                exp=payload["exp"],
            )
        except jwt.ExpiredSignatureError:
            raise ValueError("Session has expired. Please log in again.")
        except jwt.PyJWTError as e:
            raise ValueError(f"Invalid authentication token: {e}")

    async def authenticate_github_code(
        self, code: str, redirect_uri: Optional[str] = None
    ) -> Tuple[UserRecord, str]:
        """Full OAuth code authentication flow: exchange code, fetch profile, upsert user, issue JWT."""
        if not settings.github_client_id or not settings.github_client_secret:
            raise ValueError(
                "GitHub OAuth credentials are not configured. Please set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET in backend/.env"
            )

        token = await self.exchange_code_for_token(code, redirect_uri=redirect_uri)
        gh_user = await self.fetch_github_user(token)
        encrypted_token = self.encrypt_token(token)
        user = self.user_repo.upsert_user(gh_user, encrypted_token)
        jwt_token = self.create_jwt_token(user)
        return user, jwt_token
