"""Load test with the fake LLM: log in, list documents, ask a question and read the whole
SSE stream.

Run it through `make loadtest` (benchmarks/loadtest.py), which starts a dedicated API and
worker against a copy of the filings library and runs this file at fixed user counts. It
can also be pointed at any running API:

    uv run --directory backend --group bench locust -f ../benchmarks/locustfile.py \
        --host http://127.0.0.1:8002

One account is seeded per run. Each simulated user logs in with it and keeps its own
session cookie. The API under test needs a high per-user rate limit (loadtest.py sets it).

Besides the HTTP rows Locust records, each question adds two rows of type SSE:
  "ask: first token"   time from sending the question to the first token (or refusal)
  "ask: full answer"   time until the `done` event; a failure if the stream ends otherwise
"""

from __future__ import annotations

import os
import random
import time
from pathlib import Path
from typing import Any

import requests
from locust import HttpUser, between, events, task

EMAIL = os.environ.get("LOADTEST_EMAIL", "loadtest@example.org")
PASSWORD = os.environ.get("LOADTEST_PASSWORD", "load-test-password")
WORKSPACE = "Load test"
HEADERS = {"X-Requested-With": "locust"}
SAMPLE_PDF = Path(__file__).resolve().parents[1] / "backend/tests/fixtures/sample_report.pdf"

# Questions over the 10-K library: lookups, a year-over-year, a cross-company, and two the
# filings can't answer (these are refused before the LLM is called).
LIBRARY_QUESTIONS = [
    "What was Apple's total net sales in fiscal 2025?",
    "How much did Microsoft spend on research and development in fiscal 2026?",
    "What risks does Amazon describe for AWS?",
    "How did JPMorgan Chase's net income change from 2024 to 2025?",
    "Compare Apple and Microsoft revenue in fiscal 2025.",
    "What does Johnson & Johnson say about talc litigation?",
    "Who won the 2022 FIFA World Cup?",
    "What is the best recipe for sourdough bread?",
]
# Used only when the library is empty and the sample PDF is uploaded instead.
PDF_QUESTIONS = [
    "Where is the company's largest supplier located?",
    "How many retail stores does Northwind operate?",
    "Who won the 2022 FIFA World Cup?",
]

_state: dict[str, Any] = {"workspace_id": None, "questions": LIBRARY_QUESTIONS}


def _seed(host: str) -> None:
    """Create (or reuse) the account and a workspace with documents; warm up the models."""
    s = requests.Session()
    s.headers.update(HEADERS)
    creds = {"email": EMAIL, "password": PASSWORD}
    if s.post(f"{host}/auth/login", json=creds, timeout=30).status_code == 401:
        s.post(f"{host}/auth/signup", json=creds, timeout=30).raise_for_status()
    workspaces = s.get(f"{host}/workspaces", timeout=30).json()
    ws = next((w for w in workspaces if w["name"] == WORKSPACE), None)
    if ws is None:
        resp = s.post(f"{host}/workspaces", json={"name": WORKSPACE}, timeout=30)
        resp.raise_for_status()
        ws = resp.json()
    docs = s.post(f"{host}/workspaces/{ws['id']}/library", json={}, timeout=30).json()
    if not any(d["is_library"] for d in docs):
        _state["questions"] = PDF_QUESTIONS
        if not docs:
            with SAMPLE_PDF.open("rb") as fh:
                files = {"file": ("sample_report.pdf", fh, "application/pdf")}
                s.post(f"{host}/workspaces/{ws['id']}/documents", files=files, timeout=60)
        for _ in range(300):
            docs = s.get(f"{host}/workspaces/{ws['id']}/documents", timeout=30).json()
            if docs and all(d["status"] == "ready" for d in docs):
                break
            time.sleep(1)
        else:
            raise RuntimeError("the sample PDF never finished ingesting")
    # The first question loads the embedding and reranker models; keep that out of the run.
    s.post(
        f"{host}/workspaces/{ws['id']}/ask",
        json={"question": _state["questions"][0]},
        timeout=300,
    ).raise_for_status()
    _state["workspace_id"] = ws["id"]


@events.test_start.add_listener
def on_test_start(environment: Any, **_: Any) -> None:
    _seed(environment.host)


def _fire(user: HttpUser, name: str, started: float, ended: float, error: str | None) -> None:
    user.environment.events.request.fire(
        request_type="SSE",
        name=name,
        response_time=(ended - started) * 1000,
        response_length=0,
        exception=RuntimeError(error) if error else None,
        context={},
    )


class ChatUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self) -> None:
        self.client.headers.update(HEADERS)
        self.login()

    @property
    def workspace_id(self) -> str:
        return str(_state["workspace_id"])

    @task(1)
    def login(self) -> None:
        self.client.post("/auth/login", json={"email": EMAIL, "password": PASSWORD})

    @task(4)
    def list_documents(self) -> None:
        self.client.get(
            f"/workspaces/{self.workspace_id}/documents", name="/workspaces/:id/documents"
        )

    @task(2)
    def ask(self) -> None:
        question = random.choice(_state["questions"])
        started = time.perf_counter()
        first: float | None = None
        seen: list[str] = []
        error: str | None = None
        # With stream=True, Locust's own timing for this row stops at the response headers.
        with self.client.post(
            f"/workspaces/{self.workspace_id}/ask",
            json={"question": question},
            stream=True,
            catch_response=True,
            name="/workspaces/:id/ask (headers)",
        ) as resp:
            if resp.status_code != 200:
                error = f"HTTP {resp.status_code}"
                resp.failure(error)
            else:
                try:
                    for line in resp.iter_lines(decode_unicode=True):
                        if line and line.startswith("event: "):
                            event = line.removeprefix("event: ")
                            seen.append(event)
                            if first is None and event in ("token", "refusal"):
                                first = time.perf_counter()
                except requests.RequestException as exc:
                    error = f"stream broke: {type(exc).__name__}"
                if error is None and "error" in seen:
                    error = "error event"
                elif error is None and seen[-1:] != ["done"]:
                    error = "stream ended without done"
                resp.success()  # the HTTP part worked; stream problems are counted below
        ended = time.perf_counter()
        if first is not None:
            _fire(self, "ask: first token", started, first, None)
        _fire(self, "ask: full answer", started, ended, error)
