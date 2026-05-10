from __future__ import annotations

import uuid
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.mail.base import MailCredentials, MailProvider
from app.models.mail_connection import UserMailConnection

logger = logging.getLogger(__name__)

_REFRESH_THRESHOLD = timedelta(minutes=5)


def _is_expired(creds: MailCredentials) -> bool:
    if not creds.access_token or creds.expires_at is None:
        return True
    try:
        exp = creds.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        return exp <= datetime.now(timezone.utc) + _REFRESH_THRESHOLD
    except Exception:
        return True


async def store_connection(
    db: AsyncSession,
    user_id: str | uuid.UUID,
    provider: str,
    creds: MailCredentials,
) -> UserMailConnection:
    uid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
    blob = creds.to_encrypted_blob()
    scopes_str = ",".join(creds.scopes) if creds.scopes else None

    result = await db.execute(
        select(UserMailConnection).where(
            UserMailConnection.user_id == uid,
            UserMailConnection.provider == provider,
            UserMailConnection.provider_email == creds.provider_email,
        )
    )
    record = result.scalar_one_or_none()

    if record:
        record.encrypted_tokens = blob
        record.provider_user_id = creds.provider_user_id or record.provider_user_id
        record.scopes = scopes_str
        record.status = "active"
    else:
        record = UserMailConnection(
            user_id=uid,
            provider=provider,
            provider_email=creds.provider_email,
            provider_user_id=creds.provider_user_id or None,
            encrypted_tokens=blob,
            scopes=scopes_str,
            status="active",
        )
        db.add(record)

    await db.flush()
    return record


async def load_connection(
    db: AsyncSession,
    user_id: str | uuid.UUID,
    provider: str,
    provider_email: str,
) -> tuple[UserMailConnection, MailCredentials] | None:
    uid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
    result = await db.execute(
        select(UserMailConnection).where(
            UserMailConnection.user_id == uid,
            UserMailConnection.provider == provider,
            UserMailConnection.provider_email == provider_email,
            UserMailConnection.status == "active",
        )
    )
    record = result.scalar_one_or_none()
    if record is None:
        return None
    creds = MailCredentials.from_encrypted_blob(record.encrypted_tokens)
    return record, creds


async def list_connections(
    db: AsyncSession,
    user_id: str | uuid.UUID,
) -> list[UserMailConnection]:
    uid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
    result = await db.execute(
        select(UserMailConnection).where(
            UserMailConnection.user_id == uid,
            UserMailConnection.status != "revoked",
        )
    )
    return list(result.scalars().all())


async def get_connection_by_id(
    db: AsyncSession,
    connection_id: str | uuid.UUID,
    user_id: str | uuid.UUID,
) -> Optional[UserMailConnection]:
    cid = uuid.UUID(connection_id) if isinstance(connection_id, str) else connection_id
    uid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
    result = await db.execute(
        select(UserMailConnection).where(
            UserMailConnection.id == cid,
            UserMailConnection.user_id == uid,
        )
    )
    return result.scalar_one_or_none()


async def revoke_connection(
    db: AsyncSession,
    connection: UserMailConnection,
) -> None:
    connection.status = "revoked"
    connection.encrypted_tokens = ""
    await db.flush()


async def get_fresh_credentials(
    db: AsyncSession,
    user_id: str | uuid.UUID,
    provider: str,
    provider_email: str,
    mail_provider: MailProvider,
) -> tuple[UserMailConnection, MailCredentials]:
    result = await load_connection(db, user_id, provider, provider_email)
    if result is None:
        raise ValueError(f"No active {provider} connection for user {user_id}")
    record, creds = result

    if _is_expired(creds):
        creds = await mail_provider.refresh_credentials(creds)
        record.encrypted_tokens = creds.to_encrypted_blob()
        await db.flush()

    return record, creds


def load_connection_sync(
    session: Session,
    user_id: str | uuid.UUID,
    provider: str,
) -> MailCredentials:
    uid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
    record = (
        session.query(UserMailConnection)
        .filter_by(user_id=uid, provider=provider, status="active")
        .first()
    )
    if record is None:
        raise ValueError(f"No active {provider} connection for user {user_id}")
    return MailCredentials.from_encrypted_blob(record.encrypted_tokens)


def get_fresh_credentials_sync(
    session: Session,
    user_id: str | uuid.UUID,
    provider: str,
    mail_provider: MailProvider,
) -> MailCredentials:
    uid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
    record = (
        session.query(UserMailConnection)
        .filter_by(user_id=uid, provider=provider, status="active")
        .first()
    )
    if record is None:
        raise ValueError(f"No active {provider} connection for user {user_id}")

    creds = MailCredentials.from_encrypted_blob(record.encrypted_tokens)

    if _is_expired(creds):
        creds = mail_provider.refresh_credentials_sync(creds)
        record.encrypted_tokens = creds.to_encrypted_blob()
        record.updated_at = datetime.now(timezone.utc)
        session.commit()

    return creds
