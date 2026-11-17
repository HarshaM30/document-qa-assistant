from __future__ import annotations

from typing import Any

from httpx import ASGITransport, AsyncClient

from docqa.auth.deps import CSRF_HEADER

PASSWORD = "correct-horse-battery"


def make_client(app: Any) -> AsyncClient:
    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        headers={CSRF_HEADER: "XMLHttpRequest"},
    )


async def signup(client: AsyncClient, email: str, password: str = PASSWORD) -> dict[str, Any]:
    resp = await client.post("/auth/signup", json={"email": email, "password": password})
    assert resp.status_code == 201, resp.text
    body: dict[str, Any] = resp.json()
    return body


async def create_workspace(client: AsyncClient, name: str = "Research") -> dict[str, Any]:
    resp = await client.post("/workspaces", json={"name": name})
    assert resp.status_code == 201, resp.text
    body: dict[str, Any] = resp.json()
    return body
