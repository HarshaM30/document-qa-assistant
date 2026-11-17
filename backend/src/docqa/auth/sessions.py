"""Opaque session tokens.

The browser holds a random token in an HttpOnly cookie. The database stores only an
HMAC-SHA256 of it (keyed by SESSION_SECRET_KEY), so a leaked `sessions` table can't be
replayed, and rotating the key invalidates every session.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import Response
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from docqa.config import Settings
from docqa.db.models import Session, User


def new_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str, settings: Settings) -> str:
    key = settings.session_secret_key.get_secret_value().encode()
    return hmac.new(key, token.encode(), hashlib.sha256).hexdigest()


async def create_session(db: AsyncSession, user_id: uuid.UUID, settings: Settings) -> str:
    """Persist a new session and return the raw token (to be set as a cookie)."""
    token = new_token()
    db.add(
        Session(
            user_id=user_id,
            token_hash=hash_token(token, settings),
            expires_at=datetime.now(UTC) + timedelta(hours=settings.session_ttl_hours),
        )
    )
    await db.commit()
    return token


async def get_session_user(db: AsyncSession, token: str, settings: Settings) -> User | None:
    result = await db.execute(
        select(Session).where(Session.token_hash == hash_token(token, settings))
    )
    session = result.scalar_one_or_none()
    if session is None:
        return None
    if session.expires_at <= datetime.now(UTC):
        await db.delete(session)
        await db.commit()
        return None
    return session.user


async def revoke_session(db: AsyncSession, token: str, settings: Settings) -> None:
    await db.execute(delete(Session).where(Session.token_hash == hash_token(token, settings)))
    await db.commit()


def set_session_cookie(response: Response, token: str, settings: Settings) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.session_ttl_hours * 3600,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/",
    )


def clear_session_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=settings.session_cookie_name,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/",
    )
