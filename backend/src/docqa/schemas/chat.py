from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from docqa.generation.citations import Citation

MAX_QUESTION_CHARS = 2000


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=MAX_QUESTION_CHARS)

    @field_validator("question")
    @classmethod
    def _strip(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Question must not be blank")
        return value


class PassageOut(BaseModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_title: str
    section_title: str
    item_code: str | None
    page_start: int | None
    page_end: int | None
    is_table: bool
    text: str


class AnswerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    text: str
    status: Literal["complete", "stopped", "failed"]
    refused: bool
    citations: list[Citation]
    latency_ms: int | None
    created_at: datetime


class ChatTurnOut(BaseModel):
    """A stored question and its answer (None if no answer was saved, e.g. a server crash)."""

    question_id: uuid.UUID
    question: str
    asked_at: datetime
    answer: AnswerOut | None
