from __future__ import annotations

import logging

from app.mail.base import MailCredentials, MailProvider

logger = logging.getLogger(__name__)

_IMAP_HOST = "127.0.0.1"
_IMAP_PORT = 1143  # ProtonMail Bridge default


class ProtonMailProvider(MailProvider):
    provider_name = "protonmail"
    auth_type = "imap_password"

    def __init__(self, host: str = _IMAP_HOST, port: int = _IMAP_PORT) -> None:
        self._host = host
        self._port = port

    async def validate_credentials(self, creds: MailCredentials) -> bool:
        try:
            import aioimaplib
            imap = aioimaplib.IMAP4(host=self._host, port=self._port)
            await imap.wait_hello_from_server()
            result, _ = await imap.login(creds.provider_email, creds.imap_password)
            await imap.logout()
            return result == "OK"
        except Exception as exc:
            logger.warning("ProtonMail IMAP validation failed for %s: %s", creds.provider_email, exc)
            return False

    async def connect_with_password(self, provider_email: str, password: str) -> MailCredentials:
        creds = MailCredentials(
            provider_email=provider_email,
            provider_user_id=provider_email,
            imap_password=password,
            scopes=["imap"],
        )
        if not await self.validate_credentials(creds):
            raise ValueError(
                "ProtonMail IMAP login failed — ensure Bridge is running and the App Password is correct."
            )
        return creds
