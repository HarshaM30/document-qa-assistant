"""fastembed wrapper: lazily loaded ONNX embedding model plus its tokenizer.

The model is downloaded on first use into FASTEMBED_CACHE_DIR and the ONNX session is only
created when something is actually embedded, so processes that never embed (e.g. the API
before Milestone 3) pay nothing.
"""

from __future__ import annotations

import threading
from collections.abc import Callable, Sequence
from functools import lru_cache
from pathlib import Path
from typing import Any

from tokenizers import Tokenizer as HFTokenizerImpl

from docqa.config import Settings


class HFTokenizer:
    """Adapter from a Hugging Face `tokenizers.Tokenizer` to the chunker's protocol."""

    def __init__(self, tokenizer: HFTokenizerImpl) -> None:
        tokenizer.no_truncation()
        tokenizer.no_padding()
        self._tok = tokenizer

    def count_batch(self, texts: list[str]) -> list[int]:
        if not texts:
            return []
        return [len(e.ids) for e in self._tok.encode_batch(texts, add_special_tokens=False)]

    def _offsets(self, text: str) -> list[tuple[int, int]]:
        return list(self._tok.encode(text, add_special_tokens=False).offsets)

    def split(self, text: str, max_tokens: int) -> list[str]:
        offsets = self._offsets(text)
        pieces = []
        for i in range(0, len(offsets), max_tokens):
            window = offsets[i : i + max_tokens]
            end = offsets[i + max_tokens][0] if i + max_tokens < len(offsets) else len(text)
            pieces.append(text[window[0][0] : end].strip())
        return [p for p in pieces if p]

    def windows(self, text: str, size: int, overlap: int) -> list[tuple[int, int]]:
        offsets = self._offsets(text)
        if not offsets:
            return []
        spans, step = [], size - overlap
        for i in range(0, len(offsets), step):
            window = offsets[i : i + size]
            spans.append((window[0][0], window[-1][1]))
            if i + size >= len(offsets):
                break
        return spans


class Embedder:
    def __init__(
        self,
        model_name: str,
        cache_dir: Path,
        *,
        batch_size: int = 32,
        threads: int | None = None,
    ) -> None:
        self.model_name = model_name
        self.cache_dir = cache_dir
        self.batch_size = batch_size
        self.threads = threads
        self._model: Any = None
        self._tokenizer: HFTokenizer | None = None
        self._lock = threading.Lock()

    def _get_model(self) -> Any:
        with self._lock:
            if self._model is None:
                from fastembed import TextEmbedding

                self.cache_dir.mkdir(parents=True, exist_ok=True)
                self._model = TextEmbedding(
                    self.model_name,
                    cache_dir=str(self.cache_dir),
                    threads=self.threads,
                    lazy_load=True,
                )
            return self._model

    @property
    def tokenizer(self) -> HFTokenizer:
        if self._tokenizer is None:
            from fastembed.common.preprocessor_utils import load_tokenizer

            model_dir = Path(self._get_model().model._model_dir)
            tokenizer, _ = load_tokenizer(model_dir)
            self._tokenizer = HFTokenizer(tokenizer)
        return self._tokenizer

    def embed_passages(
        self,
        texts: Sequence[str],
        on_batch: Callable[[int, int], None] | None = None,
    ) -> list[list[float]]:
        """Embed passages in batches; `on_batch(done, total)` is called after each batch."""
        model = self._get_model()
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self.batch_size):
            batch = list(texts[start : start + self.batch_size])
            vectors.extend(v.tolist() for v in model.passage_embed(batch, batch_size=len(batch)))
            if on_batch:
                on_batch(min(start + self.batch_size, len(texts)), len(texts))
        return vectors

    def embed_query(self, text: str) -> list[float]:
        vector = next(iter(self._get_model().query_embed(text)))
        return list(vector.tolist())


@lru_cache(maxsize=4)
def _cached_embedder(
    model_name: str, cache_dir: str, batch_size: int, threads: int | None
) -> Embedder:
    return Embedder(model_name, Path(cache_dir), batch_size=batch_size, threads=threads)


def get_embedder(settings: Settings) -> Embedder:
    """One embedder per process and configuration (models are large; load them once)."""
    return _cached_embedder(
        settings.embedding_model,
        str(settings.fastembed_cache_dir),
        settings.embedding_batch_size,
        settings.embedding_threads,
    )
