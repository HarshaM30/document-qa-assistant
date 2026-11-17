"""Auth dependencies: current user and CSRF header check."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from docqa.auth.sessions import get_session_user
from docqa.config import Settings
from docqa.db.models import User
from docqa.db.session import get_db

CSRF_HEADER = "X-Requested-With"
_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


def get_app_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


SettingsDep = Annotated[Settings, Depends(get_app_settings)]
DbDep = Annotated[AsyncSession, Depends(get_db)]


async def csrf_protect(request: Request) -> None:
    """Require a custom header on state-changing requests.

    Browsers can't attach custom headers to cross-site form posts, and CORS preflight
    blocks them from other origins, so its presence proves a same-origin script sent it.
    """
    if request.method not in _SAFE_METHODS and not request.headers.get(CSRF_HEADER):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=f"Missing {CSRF_HEADER} header")


async def current_user(request: Request, db: DbDep, settings: SettingsDep) -> User:
    token = request.cookies.get(settings.session_cookie_name)
    if token:
        user = await get_session_user(db, token, settings)
        if user is not None:
            return user
    raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")


CurrentUser = Annotated[User, Depends(current_user)]
