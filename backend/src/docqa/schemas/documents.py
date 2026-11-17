from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: str
    stage: str
    progress: float
    attempts: int
    max_attempts: int
    error: str | None
    stage_seconds: dict[str, Any]
    pages_per_minute: float | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    filename: str
    source_type: str
    status: str
    is_library: bool
    size_bytes: int
    page_count: int | None
    ticker: str | None
    company_name: str | None
    fiscal_year: int | None
    created_at: datetime
    job: JobOut | None = None


class LibraryAttach(BaseModel):
    document_ids: list[uuid.UUID] | None = None  # None = attach the whole library
