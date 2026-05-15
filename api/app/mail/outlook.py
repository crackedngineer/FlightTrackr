from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from urllib.parse import urlencode

import httpx

from app.mail.base import MailCredentials, MailProvider

logger = logging.getLogger(__name__)

_AUTH_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
_TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
_GRAPH_ME_URL = "https://graph.microsoft.com/v1.0/me"
_SCOPES = "openid email offline_access https://outlook.office.com/Mail.ReadBasic"


class OutlookProvider(MailProvider):
    provider_name = "outlook"
    auth_type = "oauth2"

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._redirect_uri = redirect_uri

    def get_redirect_uri(self) -> str:
        return self._redirect_uri

    def get_oauth_url(self, state: str, redirect_uri: str) -> str:
        params = {
            "client_id": self._client_id,
            "redirect_uri": redirect_uri or self._redirect_uri,
            "response_type": "code",
            "scope": _SCOPES,
            "state": state,
        }
        return f"{_AUTH_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str, redirect_uri: str) -> MailCredentials:
        async with httpx.AsyncClient() as client:
            resp = await client.post(_TOKEN_URL, data={
                "code": code,
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
                "scope": _SCOPES,
            })
            resp.raise_for_status()
            data = resp.json()

        expires_at = datetime.now(timezone.utc) + timedelta(seconds=data.get("expires_in", 3600))
        user_info = await self._get_user_info(data["access_token"])
        return MailCredentials(
            provider_email=user_info.get("mail") or user_info.get("userPrincipalName", ""),
            provider_user_id=user_info.get("id", ""),
            access_token=data.get("access_token"),
            refresh_token=data.get("refresh_token"),
            expires_at=expires_at,
            scopes=_SCOPES.split(),
        )

    async def refresh_credentials(self, creds: MailCredentials) -> MailCredentials:
        if not creds.refresh_token:
            raise ValueError("No refresh token available")
        async with httpx.AsyncClient() as client:
            resp = await client.post(_TOKEN_URL, data={
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "refresh_token": creds.refresh_token,
                "grant_type": "refresh_token",
                "scope": _SCOPES,
            })
            resp.raise_for_status()
            data = resp.json()
        creds.access_token = data["access_token"]
        if "refresh_token" in data:
            creds.refresh_token = data["refresh_token"]
        creds.expires_at = datetime.now(timezone.utc) + timedelta(seconds=data.get("expires_in", 3600))
        return creds

    def refresh_credentials_sync(self, creds: MailCredentials) -> MailCredentials:
        if not creds.refresh_token:
            raise ValueError("No refresh token available")
        with httpx.Client() as client:
            resp = client.post(_TOKEN_URL, data={
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "refresh_token": creds.refresh_token,
                "grant_type": "refresh_token",
                "scope": _SCOPES,
            })
            resp.raise_for_status()
            data = resp.json()
        creds.access_token = data["access_token"]
        if "refresh_token" in data:
            creds.refresh_token = data["refresh_token"]
        creds.expires_at = datetime.now(timezone.utc) + timedelta(seconds=data.get("expires_in", 3600))
        return creds

    async def validate_credentials(self, creds: MailCredentials) -> bool:
        try:
            await self._get_user_info(creds.access_token)
            return True
        except Exception:
            return False

    async def _get_user_info(self, access_token: str) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                _GRAPH_ME_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            resp.raise_for_status()
            return resp.json()
