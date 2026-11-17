"""Test doubles shared by unit tests."""

from __future__ import annotations

import re

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
