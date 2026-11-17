"""Cross-encoder reranking with fastembed (ONNX), lazily loaded."""

from __future__ import annotations

import threading
from collections.abc import Sequence
from functools import lru_cache
from pathlib import Path
from typing import Any, Protocol

from docqa.config import Settings


class Scorer(Protocol):
    def score(self, query: str, passages: Sequence[str]) -> list[float]: ...


class CrossEncoderReranker:
    """Scores (query, passage) pairs; higher is more relevant. Scores are raw logits."""

    def __init__(
        self,
        model_name: str,
        cache_dir: Path,
        threads: int | None = None,
        batch_size: int = 4,
    ) -> None:
        self.model_name = model_name
        self.cache_dir = cache_dir
        self.threads = threads
        # Peak memory grows with batch size (512-token pairs); 4 is as fast as 16 on CPU
        # and keeps the API well under its container memory limit.
        self.batch_size = batch_size
        self._model: Any = None
        self._lock = threading.Lock()

    def _get_model(self) -> Any:
        with self._lock:
            if self._model is None:
                from fastembed.rerank.cross_encoder import TextCrossEncoder

                self.cache_dir.mkdir(parents=True, exist_ok=True)
                self._model = TextCrossEncoder(
                    self.model_name, cache_dir=str(self.cache_dir), threads=self.threads
                )
            return self._model

    def score(self, query: str, passages: Sequence[str]) -> list[float]:
        if not passages:
            return []
        return [
            float(s)
            for s in self._get_model().rerank(query, list(passages), batch_size=self.batch_size)
        ]


def rerank_order(scores: Sequence[float]) -> list[int]:
    """Indices sorted by descending score; ties keep their incoming (fused) order."""
    return sorted(range(len(scores)), key=lambda i: (-scores[i], i))


@lru_cache(maxsize=2)
def _cached(
    model_name: str, cache_dir: str, threads: int | None, batch_size: int
) -> CrossEncoderReranker:
    return CrossEncoderReranker(model_name, Path(cache_dir), threads, batch_size)


def get_reranker(settings: Settings) -> CrossEncoderReranker:
    return _cached(
        settings.reranker_model,
        str(settings.fastembed_cache_dir),
        settings.embedding_threads,
        settings.rerank_batch_size,
    )
