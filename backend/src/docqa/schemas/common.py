from __future__ import annotations

from pydantic import BaseModel


class FieldError(BaseModel):
    field: str
    message: str
    type: str | None = None


class ErrorOut(BaseModel):
    """The body of every error response (see docqa.errors)."""

    detail: str
    code: str
    request_id: str | None = None
    errors: list[FieldError] | None = None
