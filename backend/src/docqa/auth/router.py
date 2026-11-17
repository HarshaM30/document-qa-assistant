"""Signup, login, logout, and current-user endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from docqa.auth.deps import CurrentUser, DbDep, SettingsDep
from docqa.auth.passwords import hash_password, needs_rehash, verify_dummy, verify_password
from docqa.auth.sessions import (
    clear_session_cookie,
    create_session,
    revoke_session,
    set_session_cookie,
)
from docqa.db.models import User
from docqa.schemas.auth import Credentials, SignupRequest, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(
    body: SignupRequest, response: Response, db: DbDep, settings: SettingsDep
) -> UserOut:
    user = User(email=body.email, password_hash=hash_password(body.password))
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="An account with this email already exists"
        ) from None
    token = await create_session(db, user.id, settings)
    set_session_cookie(response, token, settings)
    return UserOut.model_validate(user)


@router.post("/login")
async def login(body: Credentials, response: Response, db: DbDep, settings: SettingsDep) -> UserOut:
    user = (await db.execute(select(User).where(User.email == body.email))).scalar_one_or_none()
    if user is None:
        verify_dummy(body.password)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if not verify_password(user.password_hash, body.password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(body.password)
        await db.commit()
    token = await create_session(db, user.id, settings)
    set_session_cookie(response, token, settings)
    return UserOut.model_validate(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(request: Request, response: Response, db: DbDep, settings: SettingsDep) -> None:
    token = request.cookies.get(settings.session_cookie_name)
    if token:
        await revoke_session(db, token, settings)
    clear_session_cookie(response, settings)


@router.get("/me")
async def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)
