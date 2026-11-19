"""Structured logging: one JSON object (or one key=value line) per record, with a request ID.

The request ID lives in a context variable. The API sets it per request (see
`docqa.middleware`), the worker sets it per job, and every log record carries it, so all
lines from one request or one ingestion attempt can be grepped together.
"""

from __future__ import annotations

import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

_HANDLER_NAME = "docqa"

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)

# Attributes every LogRecord has; anything else was passed via `extra=` and is emitted.
_STANDARD_ATTRS = frozenset(
    vars(logging.LogRecord("", 0, "", 0, "", None, None)).keys()
    | {"message", "asctime", "request_id", "taskName"}
)


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


def _extras(record: logging.LogRecord) -> dict[str, Any]:
    # uvicorn adds an ANSI-coloured copy of the message; LiteLLM tags records it redacted.
    return {
        k: v
        for k, v in vars(record).items()
        if k not in _STANDARD_ATTRS and k != "color_message" and not k.startswith("litellm")
    }


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        request_id = getattr(record, "request_id", None)
        if request_id:
            entry["request_id"] = request_id
        entry.update(_extras(record))
        if record.exc_info:
            entry["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(entry, default=str)


class TextFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        ts = datetime.fromtimestamp(record.created).strftime("%H:%M:%S.%f")[:-3]
        line = f"{ts} {record.levelname:<7} {record.name}: {record.getMessage()}"
        fields = _extras(record)
        request_id = getattr(record, "request_id", None)
        if request_id:
            fields = {"request_id": request_id, **fields}
        if fields:
            line += " " + " ".join(f"{k}={v}" for k, v in fields.items())
        if record.exc_info:
            line += "\n" + self.formatException(record.exc_info)
        return line


def configure_logging(level: str = "INFO", fmt: str = "json") -> None:
    """Send every logger (including uvicorn's and arq's) through one formatted handler."""
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JsonFormatter() if fmt == "json" else TextFormatter())
    handler.addFilter(RequestIdFilter())
    handler.set_name(_HANDLER_NAME)

    root = logging.getLogger()
    # Replace an earlier call's handler or a plain basicConfig() one; leave others (such
    # as pytest's capture handler) alone.
    root.handlers[:] = [
        h
        for h in root.handlers
        if h.get_name() != _HANDLER_NAME and type(h) is not logging.StreamHandler
    ]
    root.addHandler(handler)
    root.setLevel(level.upper())
    for name in ("uvicorn", "uvicorn.error", "arq", "arq.worker"):
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.propagate = True
    # The API writes its own access line (with request ID and duration); skip uvicorn's.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    for noisy in ("httpx", "httpcore", "LiteLLM", "LiteLLM Router", "LiteLLM Proxy"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
