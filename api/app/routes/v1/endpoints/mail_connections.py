from __future__ import annotations

import json
import logging
import secrets
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db_session
from app.core.redis import get_redis_client
from app.mail import registry as mail_registry
from app.services import mail_token_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/mail")

_STATE_TTL = 600  # 10 minutes


# ── Redis-backed OAuth state helpers ─────────────────────────────────────────


async def _make_state(redis: Redis, user_id: str, provider: str) -> str:
    token = secrets.token_urlsafe(32)
    await redis.setex(
        f"mail_oauth_state:{token}",
        _STATE_TTL,
        json.dumps({"user_id": user_id, "provider": provider}),
    )
    return token


async def _consume_state(redis: Redis, state: str, provider: str) -> str:
    key = f"mail_oauth_state:{state}"
    raw = await redis.get(key)
    if raw is None:
        raise HTTPException(
            status_code=400, detail="Invalid or expired OAuth state parameter."
        )
    await redis.delete(key)
    entry = json.loads(raw.decode())
    if entry["provider"] != provider:
        raise HTTPException(status_code=400, detail="OAuth state provider mismatch.")
    return entry["user_id"]


# ── Schemas ───────────────────────────────────────────────────────────────────


class ConnectResponse(BaseModel):
    auth_url: str
    state: str


class ConnectRequest(BaseModel):
    """Used only by password-based providers (e.g. ProtonMail). OAuth providers ignore this body."""

    provider_email: str | None = None
    password: str | None = None


class MailCallbackRequest(BaseModel):
    code: str
    state: str


class ConnectionOut(BaseModel):
    id: str
    provider: str
    provider_email: str
    status: str
    scopes: list[str]
    connected_at: Any
    last_synced_at: Any


# ── Helpers ───────────────────────────────────────────────────────────────────


def _connection_out(record) -> ConnectionOut:
    return ConnectionOut(
        id=str(record.id),
        provider=record.provider,
        provider_email=record.provider_email,
        status=record.status,
        scopes=record.scopes.split(",") if record.scopes else [],
        connected_at=record.connected_at,
        last_synced_at=record.last_synced_at,
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/connections", response_model=list[ConnectionOut])
async def list_connections(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> list[ConnectionOut]:
    records = await mail_token_service.list_connections(db, user_id)
    return [_connection_out(r) for r in records]


@router.post("/{provider}/connect")
async def connect_provider(
    provider: str,
    body: ConnectRequest = ConnectRequest(),
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis_client),
):
    """
    Unified connect endpoint.
    - OAuth providers (auth_type='oauth2'): returns ConnectResponse with auth_url.
    - Password providers (auth_type='imap_password'): accepts provider_email + password, returns ConnectionOut.
    """
    mail_provider = mail_registry.get(provider)

    if mail_provider.auth_type == "oauth2":
        state = await _make_state(redis, user_id, provider)
        redirect_uri = mail_provider.get_redirect_uri()
        auth_url = mail_provider.get_oauth_url(state=state, redirect_uri=redirect_uri)
        return ConnectResponse(auth_url=auth_url, state=state)

    # imap_password path
    if not body.provider_email or not body.password:
        raise HTTPException(
            status_code=422,
            detail=f"provider_email and password are required for '{provider}'.",
        )
    try:
        creds = await mail_provider.connect_with_password(
            body.provider_email, body.password
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    record = await mail_token_service.store_connection(db, user_id, provider, creds)
    await db.commit()
    return _connection_out(record)


@router.post("/{provider}/callback")
async def oauth_callback(
    provider: str,
    body: MailCallbackRequest,
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis_client),
) -> dict:
    user_id = await _consume_state(redis, body.state, provider)
    mail_provider = mail_registry.get(provider)

    if mail_provider.auth_type != "oauth2":
        raise HTTPException(
            status_code=400,
            detail=f"Provider '{provider}' does not use OAuth. Use POST /mail/{provider}/connect.",
        )

    redirect_uri = mail_provider.get_redirect_uri()
    try:
        creds = await mail_provider.exchange_code(
            code=body.code, redirect_uri=redirect_uri
        )
    except Exception as exc:
        logger.error("OAuth code exchange failed for %s: %s", provider, exc)
        raise HTTPException(
            status_code=400, detail=f"Failed to exchange OAuth code: {exc}"
        )

    connections = await mail_token_service.list_connections(db, user_id)
    is_first = not any(c.provider == provider for c in connections)

    record = await mail_token_service.store_connection(db, user_id, provider, creds)

    sync_triggered = False
    if is_first:
        sync_triggered = await mail_provider.trigger_first_sync(db, user_id)

    await db.commit()
    logger.info(
        "Mail connection stored: user=%s provider=%s email=%s",
        user_id,
        provider,
        creds.provider_email,
    )
    return {
        "message": f"{provider} connected successfully",
        "connection_id": str(record.id),
        "sync_triggered": sync_triggered,
    }


@router.delete("/connections/{connection_id}")
async def disconnect(
    connection_id: str,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    record = await mail_token_service.get_connection_by_id(db, connection_id, user_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Connection not found.")
    await mail_token_service.revoke_connection(db, record)
    await db.commit()
    return {"message": "Mail connection revoked."}
