"""Logging, error codes, model file checks, the answer deadline, and upload limits."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import threading
import time
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any, cast

import pytest

from docqa.api.chat import with_deadline
from docqa.config import Settings
from docqa.errors import error_code
from docqa.ingestion.parsed import DocumentParseError
from docqa.ingestion.pdf import parse_pdf
from docqa.log_config import JsonFormatter, RequestIdFilter, TextFormatter, request_id_var
from docqa.model_files import ModelFilesMissingError, enforce_model_files, locate
from docqa.retrieval.retriever import RetrievalConfig, Retriever

FIXTURE_PDF = Path(__file__).parents[1] / "fixtures" / "sample_report.pdf"


def _record(msg: str = "hello %s", *args: object, **extra: object) -> logging.LogRecord:
    record = logging.LogRecord("docqa.test", logging.INFO, __file__, 1, msg, args or ("x",), None)
    for key, value in extra.items():
        setattr(record, key, value)
    RequestIdFilter().filter(record)
    return record


def test_json_log_lines_carry_request_id_and_extras() -> None:
    token = request_id_var.set("req-123")
    try:
        record = _record(status=200, duration_ms=1.5)
    finally:
        request_id_var.reset(token)
    entry = json.loads(JsonFormatter().format(record))
    assert entry["msg"] == "hello x"
    assert entry["level"] == "INFO"
    assert entry["logger"] == "docqa.test"
    assert entry["request_id"] == "req-123"
    assert (entry["status"], entry["duration_ms"]) == (200, 1.5)


def test_json_log_omits_request_id_outside_a_request() -> None:
    entry = json.loads(JsonFormatter().format(_record()))
    assert "request_id" not in entry


def test_text_log_lines_are_key_value() -> None:
    token = request_id_var.set("abc")
    try:
        line = TextFormatter().format(_record(status=404))
    finally:
        request_id_var.reset(token)
    assert line.endswith("docqa.test: hello x request_id=abc status=404")


def test_error_codes() -> None:
    assert error_code(404) == "not_found"
    assert error_code(401) == "unauthorized"
    assert error_code(409) == "conflict"
    assert error_code(429) == "rate_limited"
    assert error_code(422) == "validation_error"
    assert error_code(599) == "error"


def _fake_cache(root: Path, repo: str, model_file: str) -> Path:
    path = root / f"models--{repo.replace('/', '--')}" / "snapshots" / "abc123" / model_file
    path.parent.mkdir(parents=True)
    path.write_bytes(b"onnx")
    return path


def test_locate_model_files_in_cache(tmp_path: Path) -> None:
    onnx = _fake_cache(tmp_path, "Qdrant/bge-small-en-v1.5-onnx-Q", "model_optimized.onnx")
    found = locate(tmp_path, "embedding", "BAAI/bge-small-en-v1.5")
    assert found.present
    assert found.path == onnx
    assert not locate(tmp_path, "reranker", "Xenova/ms-marco-MiniLM-L-6-v2").present
    assert not locate(tmp_path, "embedding", "no/such-model").present


def test_model_check_modes(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    def settings(mode: str) -> Settings:
        return Settings(fastembed_cache_dir=tmp_path, model_files_check=mode)

    assert enforce_model_files(settings("off")) == []
    with caplog.at_level(logging.WARNING, logger="docqa.model_files"):
        files = enforce_model_files(settings("warn"))
    assert [f.present for f in files] == [False, False]
    assert "docqa download-models" in caplog.text
    with pytest.raises(
        ModelFilesMissingError, match=re.escape("embedding model BAAI/bge-small-en-v1.5")
    ):
        enforce_model_files(settings("require"))

    _fake_cache(tmp_path, "Qdrant/bge-small-en-v1.5-onnx-Q", "model_optimized.onnx")
    # The worker only embeds, so it doesn't need the reranker.
    assert enforce_model_files(settings("require"), need_reranker=False)[0].present


class _Slow:
    def __init__(self, delay: float, items: int) -> None:
        self.delay, self.items = delay, items
        self.closed = False
        self.yielded = 0

    async def gen(self) -> AsyncIterator[int]:
        try:
            for i in range(self.items):
                await asyncio.sleep(self.delay)
                self.yielded += 1
                yield i
        finally:
            self.closed = True


async def test_with_deadline_passes_items_through() -> None:
    source = _Slow(0, 3)
    assert [i async for i in with_deadline(source.gen(), 1.0)] == [0, 1, 2]
    assert source.closed


async def _consume(items: AsyncIterator[int], seen: list[int], pause: float = 0) -> None:
    async for item in items:
        seen.append(item)
        if pause:
            await asyncio.sleep(pause)


async def test_with_deadline_times_out_and_closes_the_source() -> None:
    source = _Slow(0.05, 100)
    seen: list[int] = []
    with pytest.raises(TimeoutError):
        await _consume(with_deadline(source.gen(), 0.2), seen)
    assert 1 <= len(seen) < 10
    assert source.closed


async def test_with_deadline_does_not_fire_while_the_consumer_is_busy() -> None:
    # Time spent by the caller between items still counts toward the deadline, but the
    # timeout is raised from the next anext(), never inside the caller's own code.
    source = _Slow(0, 5)
    seen: list[int] = []
    with pytest.raises(TimeoutError):
        await _consume(with_deadline(source.gen(), 0.1), seen, pause=0.06)
    assert seen == [0, 1]


def test_pdf_page_limit() -> None:
    assert parse_pdf(FIXTURE_PDF, max_pages=10).page_count == 3
    with pytest.raises(DocumentParseError, match="The PDF has 3 pages; the limit is 2"):
        parse_pdf(FIXTURE_PDF, max_pages=2)


async def test_inference_cap_limits_concurrent_model_calls() -> None:
    lock = threading.Lock()
    running = peak = 0

    def model_call(seconds: float) -> float:
        nonlocal running, peak
        with lock:
            running += 1
            peak = max(peak, running)
        time.sleep(seconds)
        with lock:
            running -= 1
        return seconds

    retriever = Retriever(
        cast(Any, None), cast(Any, None), RetrievalConfig("k"), max_concurrent_inference=2
    )
    results = await asyncio.gather(*(retriever._infer(model_call, 0.05) for _ in range(6)))
    assert results == [0.05] * 6
    assert peak == 2

    # A cancelled request's thread keeps its slot until it actually finishes.
    first = asyncio.create_task(retriever._infer(model_call, 0.2))
    second = asyncio.create_task(retriever._infer(model_call, 0.2))
    await asyncio.sleep(0.05)
    first.cancel()
    third = asyncio.create_task(retriever._infer(model_call, 0.01))
    await asyncio.sleep(0.05)
    assert not third.done()  # still waiting: both slots are busy
    await asyncio.gather(second, third)
    assert peak == 2
