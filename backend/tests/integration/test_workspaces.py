from __future__ import annotations

from httpx import AsyncClient

from tests.integration.helpers import create_workspace, signup


async def test_workspace_crud(client: AsyncClient) -> None:
    await signup(client, "owner@example.org")
    ws = await create_workspace(client, "  Filings  ")
    assert ws["name"] == "Filings"

    listed = (await client.get("/workspaces")).json()
    assert [w["id"] for w in listed] == [ws["id"]]

    renamed = await client.patch(f"/workspaces/{ws['id']}", json={"name": "10-K research"})
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "10-K research"

    assert (await client.delete(f"/workspaces/{ws['id']}")).status_code == 204
    assert (await client.get(f"/workspaces/{ws['id']}")).status_code == 404


async def test_duplicate_workspace_name_conflicts(client: AsyncClient) -> None:
    await signup(client, "owner@example.org")
    await create_workspace(client, "Same")
    assert (await client.post("/workspaces", json={"name": "Same"})).status_code == 409


async def test_blank_name_rejected(client: AsyncClient) -> None:
    await signup(client, "owner@example.org")
    assert (await client.post("/workspaces", json={"name": "   "})).status_code == 422


async def test_requires_authentication(client: AsyncClient) -> None:
    assert (await client.get("/workspaces")).status_code == 401
    assert (await client.post("/workspaces", json={"name": "x"})).status_code == 401


async def test_user_cannot_access_another_users_workspace(
    client: AsyncClient, other_client: AsyncClient
) -> None:
    await signup(client, "a@example.org")
    await signup(other_client, "b@example.org")
    ws_b = await create_workspace(other_client, "B private")

    url = f"/workspaces/{ws_b['id']}"
    assert (await client.get(url)).status_code == 404
    assert (await client.patch(url, json={"name": "hijacked"})).status_code == 404
    assert (await client.delete(url)).status_code == 404
    assert (await client.get("/workspaces")).json() == []

    # B's workspace is untouched.
    assert (await other_client.get(url)).json()["name"] == "B private"
