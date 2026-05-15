import secrets
import hashlib
import base64
import logging
from typing import Optional
from supabase import Client
from supabase_auth import CodeExchangeParams
from supabase_auth.types import Session
from app.core.exceptions import AuthenticationException
from redis.asyncio import Redis
from supabase_auth import SignInWithOAuthCredentials, SignInWithOAuthCredentialsOptions
from supabase_auth.types import AuthResponse

logger = logging.getLogger(__name__)


def generate_pkce_pair():
    # Create a secure random verifier
    verifier = secrets.token_urlsafe(64)
    # Hash it with SHA256 to create the challenge
    sha256_hash = hashlib.sha256(verifier.encode("utf-8")).digest()
    challenge = base64.urlsafe_b64encode(sha256_hash).decode("utf-8").replace("=", "")
    return verifier, challenge


class AuthService:
    def __init__(self, supabase_client: Client, redis_client: Redis):
        self.supabase_client = supabase_client
        self.redis_client = redis_client

    async def authenticate_with_google(self, request_gmail_access: bool) -> dict:
        from app.core.settings import get_settings

        settings = get_settings()

        # 1. Generate PKCE and Flow ID
        code_verifier, code_challenge = generate_pkce_pair()
        state = secrets.token_urlsafe(32)

        options: SignInWithOAuthCredentialsOptions = {
            "query_params": {
                "scope": "openid email profile",
                "access_type": "offline",
                "prompt": "consent",
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
            },
        }
        if request_gmail_access:
            options["query_params"][
                "scope"
            ] += " https://www.googleapis.com/auth/gmail.readonly"
        if settings.google_redirect_uri:
            options["redirect_to"] = (
                settings.google_redirect_uri
                + "?state="
                + state
                + "&request_gmail_access="
                + str(request_gmail_access).lower()
            )
        result = self.supabase_client.auth.sign_in_with_oauth(
            SignInWithOAuthCredentials(provider="google", options=options)
        )
        if not result:
            raise AuthenticationException("OAuth authentication failed")

        await self.redis_client.setex(f"pkce_flow:{state}", 300, str(code_verifier))

        return {"url": result.url}

    async def get_current_user(self, access_token: str) -> dict:
        resp = self.supabase_client.auth.get_user(access_token)
        if not resp or not resp.user:
            raise AuthenticationException("Invalid or expired token")
        return {
            "id": resp.user.id,
            "email": resp.user.email,
            "user_metadata": resp.user.user_metadata,
            "app_metadata": resp.user.app_metadata,
        }

    async def refresh_token(self, refresh_token: str) -> AuthResponse:
        try:
            result = self.supabase_client.auth.refresh_session(refresh_token)
        except Exception as e:
            raise AuthenticationException(f"Token refresh failed: {e}") from e
        if not result or not result.session:
            raise AuthenticationException("Token refresh failed")
        return result

    async def sign_out(self) -> None:
        self.supabase_client.auth.sign_out()

    async def exchange_code_for_session(
        self, code: str, redirect_url: str, state: str
    ) -> AuthResponse:
        # 1. Retrieve the verifier from Redis using flow_id
        code_verifier_bytes = await self.redis_client.get(f"pkce_flow:{state}")

        if not code_verifier_bytes:
            raise AuthenticationException(
                "Authentication flow expired or invalid flow_id"
            )

        code_verifier = code_verifier_bytes.decode("utf-8")
        result = self.supabase_client.auth.exchange_code_for_session(
            CodeExchangeParams(
                **{
                    "auth_code": code,
                    "redirect_to": redirect_url,
                    "code_verifier": code_verifier,
                }
            )
        )
        if not result or not result.session:
            raise AuthenticationException("Code exchange failed")
        return result

    def get_google_tokens(self, session: Session) -> tuple[str, Optional[str]]:
        """Extract provider tokens from the session."""
        if not session.provider_token or not session.provider_refresh_token:
            raise AuthenticationException("No provider token found in session")
        return str(session.provider_refresh_token), str(session.provider_token)
