"""Test doubles shared by unit tests."""

from __future__ import annotations

import re
import uuid
from typing import Any

from docqa.retrieval.retriever import Passage

_WORD = re.compile(r"\S+")


class WhitespaceTokenizer:
    """One token per whitespace-separated word; implements the chunker's Tokenizer protocol."""

    def count_batch(self, texts: list[str]) -> list[int]:
        return [len(_WORD.findall(t)) for t in texts]

    def _spans(self, text: str) -> list[tuple[int, int]]:
        return [m.span() for m in _WORD.finditer(text)]

    def split(self, text: str, max_tokens: int) -> list[str]:
        spans = self._spans(text)
        return [
            text[spans[i][0] : spans[min(i + max_tokens, len(spans)) - 1][1]]
            for i in range(0, len(spans), max_tokens)
        ]

    def windows(self, text: str, size: int, overlap: int) -> list[tuple[int, int]]:
        spans = self._spans(text)
        out = []
        for i in range(0, len(spans), size - overlap):
            window = spans[i : i + size]
            out.append((window[0][0], window[-1][1]))
            if i + size >= len(spans):
                break
        return out


def make_passage(n: int, text: str = "", rerank_score: float | None = None, **kw: Any) -> Passage:
    """A retrieved passage with deterministic ids, for generation tests."""
    return Passage(
        chunk_id=uuid.UUID(int=n),
        document_id=uuid.UUID(int=1000 + n),
        document_title=kw.pop("document_title", "Acme Corp 10-K FY2025"),
        section_title=kw.pop("section_title", f"Item {n}"),
        item_code=kw.pop("item_code", str(n)),
        page_start=kw.pop("page_start", n),
        page_end=kw.pop("page_end", n),
        heading=kw.pop("heading", ""),
        text=text or f"Passage number {n}.",
        is_table=kw.pop("is_table", False),
        fused_score=kw.pop("fused_score", 1.0 / n),
        rerank_score=rerank_score,
        **kw,
    )
