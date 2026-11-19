"""Error schema, request IDs, body-size limits, and the last-resort 500 handler."""

from __future__ import annotations

import logging
import re

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from docqa.middleware import DEFAULT_MAX_BODY_BYTES
from tests.integration.helpers import make_client, signup

HEX_ID = re.compile(r"^[0-9a-f]{32}$")


async def test_errors_share_one_shape(client: AsyncClient) -> None:
    resp = await client.get("/auth/me")
    assert resp.status_code == 401
    body = resp.json()
    assert body == {
        "detail": "Not authenticated",
        "code": "unauthorized",
        "request_id": resp.headers["x-request-id"],
    }

    await signup(client, "someone@example.org")
    missing = await client.get("/workspaces/00000000-0000-0000-0000-000000000000")
    assert missing.status_code == 404
    assert missing.json()["code"] == "not_found"
    assert missing.json()["detail"] == "Workspace not found"


async def test_validation_errors_are_a_readable_string_without_the_input(
    client: AsyncClient,
) -> None:
    resp = await client.post("/auth/signup", json={"email": "nope", "password": "hunter2-secret"})
    assert resp.status_code == 422
    body = resp.json()
    assert body["code"] == "validation_error"
    assert isinstance(body["detail"], str)
    assert body["detail"].startswith("email: ")
    assert body["errors"][0]["field"] == "email"
    assert "hunter2-secret" not in resp.text


async def test_request_id_is_generated_or_propagated(client: AsyncClient) -> None:
    generated = (await client.get("/health")).headers["x-request-id"]
    assert HEX_ID.match(generated)
    passed = await client.get("/health", headers={"X-Request-ID": "lb-trace.42"})
    assert passed.headers["x-request-id"] == "lb-trace.42"
    # Anything that could forge log lines is replaced.
    unsafe = await client.get("/health", headers={"X-Request-ID": 'x" level=ERROR'})
    assert HEX_ID.match(unsafe.headers["x-request-id"])


async def test_access_log_line_per_request(
    client: AsyncClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger="docqa.access"):
        resp = await client.get("/health")
    [record] = [r for r in caplog.records if r.name == "docqa.access"]
    assert record.getMessage() == "GET /health 200"
    assert record.__dict__["status"] == 200
    assert record.__dict__["duration_ms"] >= 0
    assert resp.status_code == 200


async def test_oversized_bodies_rejected_before_parsing(client: AsyncClient) -> None:
    resp = await client.post(
        "/auth/login",
        content=b"{" + b" " * DEFAULT_MAX_BODY_BYTES + b"}",
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 413
    assert resp.json()["code"] == "content_too_large"


async def test_unhandled_exception_returns_json_500_and_is_logged_once(
    app: FastAPI, caplog: pytest.LogCaptureFixture
) -> None:
    async def explode() -> None:
        raise RuntimeError("kaboom")

    app.add_api_route("/test-explode", explode)
    async with make_client(app) as c:
        with caplog.at_level(logging.ERROR):
            resp = await c.get("/test-explode")
    assert resp.status_code == 500
    assert resp.json() == {
        "detail": "Internal server error",
        "code": "internal_error",
        "request_id": resp.headers["x-request-id"],
    }
    assert "kaboom" not in resp.text
    errors = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert len(errors) == 1
    assert errors[0].name == "docqa.errors"
