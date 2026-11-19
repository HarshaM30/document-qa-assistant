"""One error shape for every API failure: {"detail", "code", "request_id"} (+ "errors" on 422).

`detail` stays a human-readable string (the frontend shows it as is), `code` is a stable
machine-readable slug, and `request_id` matches the X-Request-ID header and the log lines.
"""

from __future__ import annotations

from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from docqa.log_config import request_id_var

_CODES = {429: "rate_limited", 413: "content_too_large", 422: "validation_error"}


def error_code(status: int) -> str:
    if status in _CODES:
        return _CODES[status]
    try:
        return HTTPStatus(status).phrase.lower().replace(" ", "_").replace("-", "_")
    except ValueError:
        return "error"


def error_body(status: int, detail: str, **extra: Any) -> dict[str, Any]:
    return {
        "detail": detail,
        "code": error_code(status),
        "request_id": request_id_var.get(),
    } | extra


def _field(loc: tuple[Any, ...] | list[Any]) -> str:
    parts = [str(p) for p in loc if p not in ("body", "query", "path")]
    return ".".join(parts)


async def _http_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    detail = exc.detail if isinstance(exc.detail, str) else HTTPStatus(exc.status_code).phrase
    return JSONResponse(
        error_body(exc.status_code, detail),
        status_code=exc.status_code,
        headers=getattr(exc, "headers", None),
    )


async def _validation_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    # The submitted input is deliberately not echoed back (it may hold a password).
    errors = [
        {"field": _field(e.get("loc", ())), "message": str(e.get("msg", "")), "type": e.get("type")}
        for e in exc.errors()
    ]
    detail = "; ".join(
        f"{e['field']}: {e['message']}" if e["field"] else e["message"] for e in errors
    )
    return JSONResponse(error_body(422, detail or "Invalid request", errors=errors), 422)


def install_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(StarletteHTTPException, _http_error)
    app.add_exception_handler(RequestValidationError, _validation_error)
