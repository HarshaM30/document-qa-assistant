from __future__ import annotations

import uuid

from pydantic import BaseModel, Field, field_validator

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
