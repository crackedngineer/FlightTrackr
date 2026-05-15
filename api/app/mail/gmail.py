from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from urllib.parse import urlencode

import httpx

from app.mail.base import MailCredentials, MailProvider

logger = logging.getLogger(__name__)

_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_TOKEN_URL = "https://oauth2.googleapis.com/token"
_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
_SCOPES = "openid email https://www.googleapis.com/auth/gmail.readonly"


class GmailProvider(MailProvider):
    provider_name = "gmail"
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
            "access_type": "offline",
            "prompt": "consent",
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
            })
            resp.raise_for_status()
            data = resp.json()

        expires_at = datetime.now(timezone.utc) + timedelta(seconds=data.get("expires_in", 3600))
        user_info = await self._get_user_info(data["access_token"])
        return MailCredentials(
            provider_email=user_info.get("email", ""),
            provider_user_id=user_info.get("sub", ""),
            access_token=data.get("access_token"),
            refresh_token=data.get("refresh_token"),
            expires_at=expires_at,
            scopes=data.get("scope", _SCOPES).split(),
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
            })
            resp.raise_for_status()
            data = resp.json()
        creds.access_token = data["access_token"]
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
            })
            resp.raise_for_status()
            data = resp.json()
        creds.access_token = data["access_token"]
        creds.expires_at = datetime.now(timezone.utc) + timedelta(seconds=data.get("expires_in", 3600))
        return creds

    async def trigger_first_sync(self, db, user_id: str) -> bool:
        import uuid as _uuid
        from app.models.gmail_sync_job import GmailSyncJob
        from app.tasks.gmail_sync import sync_gmail_boarding_passes

        job = GmailSyncJob(user_id=_uuid.UUID(user_id), status="pending")
        db.add(job)
        await db.flush()
        task = sync_gmail_boarding_passes.delay(user_id, str(job.id))
        job.celery_task_id = task.id
        logger.info("First Gmail connect — auto-sync job=%s user=%s", job.id, user_id)
        return True

    async def validate_credentials(self, creds: MailCredentials) -> bool:
        if not creds.access_token:
            return False
        try:
            await self._get_user_info(creds.access_token)
            return True
        except Exception:
            return False

    async def _get_user_info(self, access_token: str) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                _USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            resp.raise_for_status()
            return resp.json()
