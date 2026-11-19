"""ASGI middleware: request IDs, access logging, body-size limits, and a last-resort 500.

Written as plain ASGI (not `BaseHTTPMiddleware`) so streamed SSE responses pass through
untouched and the request ID context variable is visible inside the stream.
"""

from __future__ import annotations

import json
import logging
import re
import time
import uuid
from typing import Any

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from docqa.log_config import request_id_var

log = logging.getLogger("docqa.access")
error_log = logging.getLogger("docqa.errors")

REQUEST_ID_HEADER = "X-Request-ID"
_VALID_REQUEST_ID = re.compile(r"^[A-Za-z0-9._:-]{1,64}$")
_UPLOAD_PATH = re.compile(r"^/workspaces/[^/]+/documents/?$")
_MULTIPART_OVERHEAD = 1 << 20
DEFAULT_MAX_BODY_BYTES = 1 << 20


def _incoming_request_id(scope: Scope) -> str | None:
    wanted = REQUEST_ID_HEADER.lower().encode()
    for name, value in scope.get("headers", []):
        if name == wanted:
            candidate = value.decode("latin-1")
            return candidate if _VALID_REQUEST_ID.match(candidate) else None
    return None


def _content_length(scope: Scope) -> int | None:
    for name, value in scope.get("headers", []):
        if name == b"content-length":
            try:
                return int(value)
            except ValueError:
                return None
    return None


async def send_json_error(
    send: Send, status: int, detail: str, code: str, request_id: str | None, headers: Any = ()
) -> None:
    body = json.dumps({"detail": detail, "code": code, "request_id": request_id}).encode()
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
                *headers,
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp, max_upload_bytes: int) -> None:
        self.app = app
        self.max_upload_bytes = max_upload_bytes

    def _body_limit(self, scope: Scope) -> int:
        if scope["method"] == "POST" and _UPLOAD_PATH.match(scope["path"]):
            return self.max_upload_bytes + _MULTIPART_OVERHEAD
        return DEFAULT_MAX_BODY_BYTES

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = _incoming_request_id(scope) or uuid.uuid4().hex
        token = request_id_var.set(request_id)
        started = time.monotonic()
        status = 0
        id_header = (REQUEST_ID_HEADER.lower().encode(), request_id.encode())

        async def send_with_id(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                message["headers"] = [*message.get("headers", []), id_header]
            await send(message)

        try:
            length = _content_length(scope)
            if length is not None and length > self._body_limit(scope):
                status = 413
                await send_json_error(
                    send,
                    413,
                    "Request body is too large",
                    "content_too_large",
                    request_id,
                    [id_header],
                )
                return
            await self.app(scope, receive, send_with_id)
        except Exception:
            error_log.exception("unhandled error on %s %s", scope["method"], scope["path"])
            if status == 0:
                status = 500
                await send_json_error(
                    send, 500, "Internal server error", "internal_error", request_id, [id_header]
                )
            # If the response already started (mid-stream), the connection just closes.
        finally:
            log.info(
                "%s %s %s",
                scope["method"],
                scope["path"],
                status,
                extra={
                    "method": scope["method"],
                    "path": scope["path"],
                    "status": status,
                    "duration_ms": round((time.monotonic() - started) * 1000, 1),
                },
            )
            request_id_var.reset(token)
