"""Parse `[n]` citation markers and map them to the passages they reference."""

from __future__ import annotations

import re
import uuid
from collections.abc import Sequence
from typing import Any

from pydantic import BaseModel

from docqa.retrieval.retriever import Passage

# [1], [1, 3], [1,3]; adjacent markers like [1][3] are simply two matches. gpt-oss sometimes
# appends a line reference after a dagger, e.g. [1†L9-L10]; the passage number still counts.
_MARKER = re.compile(r"\[\s*(\d+(?:\s*,\s*\d+)*)\s*(?:\u2020[^\]]*)?\]")

# Some models (gpt-oss among them) cite with CJK lenticular or fullwidth brackets.
_BRACKETS = str.maketrans({"\u3010": "[", "\u3011": "]", "\uff3b": "[", "\uff3d": "]"})


def normalize_markers(text: str) -> str:
    """Rewrite bracket variants to ASCII so markers read and parse as [n]."""
    return text.translate(_BRACKETS)


class Citation(BaseModel):
    marker: int
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_title: str
    section_title: str
    item_code: str | None
    page_start: int | None
    page_end: int | None


def parse_markers(text: str) -> list[int]:
    """Marker numbers in order of first appearance, without duplicates."""
    seen: dict[int, None] = {}
    for match in _MARKER.finditer(normalize_markers(text)):
        for number in match.group(1).split(","):
            seen.setdefault(int(number), None)
    return list(seen)


def resolve_citations(text: str, passages: Sequence[Passage]) -> list[Citation]:
    """Citations for markers that point at a real passage; others are dropped."""
    citations = []
    for marker in parse_markers(text):
        if not 1 <= marker <= len(passages):
            continue
        p = passages[marker - 1]
        citations.append(
            Citation(
                marker=marker,
                chunk_id=p.chunk_id,
                document_id=p.document_id,
                document_title=p.document_title,
                section_title=p.section_title,
                item_code=p.item_code,
                page_start=p.page_start,
                page_end=p.page_end,
            )
        )
    return citations


def citations_json(citations: Sequence[Citation]) -> list[dict[str, Any]]:
    return [c.model_dump(mode="json") for c in citations]
