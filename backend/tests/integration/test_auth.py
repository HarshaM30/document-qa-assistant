from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from docqa.config import Settings
from docqa.db.models import Session, User
from tests.integration.helpers import PASSWORD, signup


async def test_signup_login_me_logout_flow(client: AsyncClient, settings: Settings) -> None:
    user = await signup(client, "Alice@Example.org")
    assert user["email"] == "alice@example.org"

    me = await client.get("/auth/me")
    assert me.status_code == 200
    assert me.json()["id"] == user["id"]

    assert (await client.post("/auth/logout")).status_code == 204
    assert (await client.get("/auth/me")).status_code == 401

    login = await client.post(
        "/auth/login", json={"email": "alice@example.org", "password": PASSWORD}
    )
    assert login.status_code == 200
    assert (await client.get("/auth/me")).json()["email"] == "alice@example.org"

    assert (await client.post("/auth/logout")).status_code == 204
    assert (await client.get("/auth/me")).status_code == 401


async def test_logout_revokes_session_server_side(
    client: AsyncClient, settings: Settings, db_sessionmaker: async_sessionmaker[AsyncSession]
) -> None:
    await signup(client, "bob@example.org")
    token = client.cookies.get(settings.session_cookie_name)
    assert token
    await client.post("/auth/logout")

    # Replaying the old token must fail even if the browser kept the cookie.
    client.cookies.set(settings.session_cookie_name, token)
    assert (await client.get("/auth/me")).status_code == 401
    async with db_sessionmaker() as db:
        assert (await db.execute(select(Session))).scalars().all() == []


async def test_duplicate_email_rejected(client: AsyncClient) -> None:
    await signup(client, "carol@example.org")
    resp = await client.post(
        "/auth/signup", json={"email": "CAROL@example.org", "password": "another-password"}
    )
    assert resp.status_code == 409


async def test_wrong_password_rejected(client: AsyncClient) -> None:
    await signup(client, "dave@example.org")
    await client.post("/auth/logout")
    resp = await client.post("/auth/login", json={"email": "dave@example.org", "password": "nope"})
    assert resp.status_code == 401
    assert (await client.get("/auth/me")).status_code == 401


async def test_unknown_email_rejected_with_same_message(client: AsyncClient) -> None:
    resp = await client.post("/auth/login", json={"email": "ghost@example.org", "password": "x"})
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid email or password"


async def test_short_password_rejected(client: AsyncClient) -> None:
    resp = await client.post("/auth/signup", json={"email": "eve@example.org", "password": "short"})
    assert resp.status_code == 422


async def test_password_stored_as_argon2id(
    client: AsyncClient, db_sessionmaker: async_sessionmaker[AsyncSession]
) -> None:
    await signup(client, "frank@example.org")
    async with db_sessionmaker() as db:
        user = (await db.execute(select(User))).scalar_one()
    assert user.password_hash.startswith("$argon2id$")
    assert PASSWORD not in user.password_hash


async def test_session_token_hashed_at_rest(
    client: AsyncClient, settings: Settings, db_sessionmaker: async_sessionmaker[AsyncSession]
) -> None:
    await signup(client, "grace@example.org")
    token = client.cookies.get(settings.session_cookie_name)
    async with db_sessionmaker() as db:
        stored = (await db.execute(select(Session))).scalar_one()
    assert token
    assert stored.token_hash != token
    assert len(stored.token_hash) == 64


async def test_session_cookie_flags(client: AsyncClient, settings: Settings) -> None:
    resp = await client.post(
        "/auth/signup", json={"email": "heidi@example.org", "password": PASSWORD}
    )
    cookie = resp.headers["set-cookie"].lower()
    assert f"{settings.session_cookie_name}=" in cookie
    assert "httponly" in cookie
    assert "samesite=lax" in cookie
    assert "secure" not in cookie  # SESSION_COOKIE_SECURE=false in tests


async def test_secure_cookie_when_configured(settings: Settings) -> None:
    from docqa.main import create_app
    from tests.integration.helpers import make_client

    app = create_app(settings.model_copy(update={"session_cookie_secure": True}))
    async with app.router.lifespan_context(app), make_client(app) as c:
        resp = await c.post(
            "/auth/signup", json={"email": "ivan@example.org", "password": PASSWORD}
        )
    assert "; secure" in resp.headers["set-cookie"].lower()


async def test_state_changing_request_without_csrf_header_rejected(client: AsyncClient) -> None:
    resp = await client.post(
        "/auth/signup",
        json={"email": "judy@example.org", "password": PASSWORD},
        headers={"X-Requested-With": ""},
    )
    assert resp.status_code == 403
