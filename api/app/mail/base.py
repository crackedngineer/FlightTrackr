from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class MailCredentials:
    provider_email: str
    provider_user_id: str = ""
    access_token: str | None = None
    refresh_token: str | None = None
    expires_at: datetime | None = None
    imap_password: str | None = None
    scopes: list[str] = field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps({
            "provider_email": self.provider_email,
            "provider_user_id": self.provider_user_id,
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "imap_password": self.imap_password,
            "scopes": self.scopes,
        })

    @classmethod
    def from_json(cls, raw: str) -> MailCredentials:
        data = json.loads(raw)
        expires_at = data.get("expires_at")
        return cls(
            provider_email=data.get("provider_email", ""),
            provider_user_id=data.get("provider_user_id", ""),
            access_token=data.get("access_token"),
            refresh_token=data.get("refresh_token"),
            expires_at=datetime.fromisoformat(expires_at) if expires_at else None,
            imap_password=data.get("imap_password"),
            scopes=data.get("scopes", []),
        )

    def to_encrypted_blob(self) -> str:
        from app.services.oauth_token_service import encrypt_token
        return encrypt_token(self.to_json())

    @classmethod
    def from_encrypted_blob(cls, blob: str) -> MailCredentials:
        from app.services.oauth_token_service import decrypt_token
        return cls.from_json(decrypt_token(blob))


class MailProvider(ABC):
    provider_name: str
    auth_type: str  # 'oauth2' | 'imap_password'

    # ── OAuth strategy methods (implement for auth_type == 'oauth2') ──────────

    def get_oauth_url(self, state: str, redirect_uri: str) -> str:
        raise NotImplementedError(f"{self.provider_name} does not support OAuth")

    def get_redirect_uri(self) -> str:
        raise NotImplementedError(f"{self.provider_name} does not support OAuth")

    async def exchange_code(self, code: str, redirect_uri: str) -> MailCredentials:
        raise NotImplementedError(f"{self.provider_name} does not support OAuth")

    # ── Password/IMAP strategy method (implement for auth_type == 'imap_password') ──

    async def connect_with_password(self, provider_email: str, password: str) -> MailCredentials:
        raise NotImplementedError(f"{self.provider_name} does not support password auth")

    # ── Post-connect hook (override to trigger provider-specific side effects) ─

    async def trigger_first_sync(self, db, user_id: str) -> bool:
        """Called after the first successful connection. Returns True if a sync was queued."""
        return False

    # ── Token lifecycle ───────────────────────────────────────────────────────

    async def refresh_credentials(self, creds: MailCredentials) -> MailCredentials:
        return creds

    def refresh_credentials_sync(self, creds: MailCredentials) -> MailCredentials:
        raise NotImplementedError(f"{self.provider_name} does not implement sync token refresh")

    @abstractmethod
    async def validate_credentials(self, creds: MailCredentials) -> bool:
        ...
