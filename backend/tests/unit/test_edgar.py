from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest
from typer.testing import CliRunner

from docqa.ingestion import edgar
from docqa.ingestion.edgar import (
    EdgarClient,
    EdgarError,
    LockEntry,
    Lockfile,
    TokenBucket,
    archive_url,
    select_filings,
    sha256_bytes,
)


def block(*rows: tuple[str, str, str, str]) -> dict[str, list[str]]:
    """rows: (accession, form, filing date, report date)."""
    return {
        "accessionNumber": [r[0] for r in rows],
        "form": [r[1] for r in rows],
        "filingDate": [r[2] for r in rows],
        "reportDate": [r[3] for r in rows],
        "primaryDocument": [f"doc-{r[0]}.htm" for r in rows],
    }


def test_select_filings_excludes_amendments_and_takes_latest() -> None:
    recent = block(
        ("a5", "8-K", "2026-02-01", ""),
        ("a4", "10-K", "2026-01-30", "2025-12-31"),
        ("a3", "10-K/A", "2025-04-01", "2024-12-31"),
        ("a2", "10-K", "2025-01-30", "2024-12-31"),
        ("a1", "10-K", "2024-01-30", "2023-12-31"),
        ("a0", "10-K", "2023-01-30", "2022-12-31"),
    )
    picked = select_filings([recent], "10-K", 3)
    assert [p.accession_number for p in picked] == ["a4", "a2", "a1"]


def test_select_filings_reads_older_pages_lazily() -> None:
    pages_read: list[int] = []

    def pages() -> Any:
        for i, b in enumerate(
            [
                block(("x3", "10-K", "2026-01-30", "2025-12-31")),
                block(("x2", "10-K", "2025-01-30", "2024-12-31")),
                block(("x1", "10-K", "2024-01-30", "2023-12-31")),
                block(("x0", "10-K", "2023-01-30", "2022-12-31")),
            ]
        ):
            pages_read.append(i)
            yield b

    assert [p.accession_number for p in select_filings(pages(), "10-K", 3)] == ["x3", "x2", "x1"]
    assert pages_read == [0, 1, 2]


def test_fiscal_year_and_urls() -> None:
    assert edgar.fiscal_year_of("2026-09-26") == 2026
    assert archive_url(320193, "0000320193-26-000026", "aapl-20260926.htm") == (
        "https://www.sec.gov/Archives/edgar/data/320193/000032019326000026/aapl-20260926.htm"
    )
    assert edgar.local_name("AAPL", 2026, "aapl-20260926.htm") == "AAPL/AAPL-10K-FY2026.htm"


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def time(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def test_token_bucket_spaces_requests() -> None:
    clock = FakeClock()
    bucket = TokenBucket(5, clock=clock.time, sleep=clock.sleep)
    for _ in range(11):
        bucket.acquire()
    # First request is free; the next ten are spaced 0.2s apart: 11 requests in 2 seconds.
    assert clock.now == pytest.approx(2.0)


def _client(handler: Any, sleeps: list[float] | None = None) -> EdgarClient:
    log = sleeps if sleeps is not None else []
    return EdgarClient(
        "Test Suite test@example.org",
        9.0,
        http=httpx.Client(transport=httpx.MockTransport(handler)),
        sleep=log.append,
        backoff_base_seconds=1.0,
        max_retries=3,
    )


def test_client_sends_user_agent_and_retries_429_with_retry_after() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(429, headers={"Retry-After": "7"})
        if len(calls) == 2:
            return httpx.Response(503)
        return httpx.Response(200, json={"ok": True})

    sleeps: list[float] = []
    client = _client(handler, sleeps)
    assert client.get_json("https://data.sec.gov/x") == {"ok": True}
    assert calls[0].headers["User-Agent"] == "Test Suite test@example.org"
    assert sleeps == [7.0, 2.0]  # Retry-After honoured, then 1s * 2**1 backoff
    assert client.stats.retries == 2


def test_client_gives_up_and_does_not_retry_404() -> None:
    client = _client(lambda r: httpx.Response(500))
    with pytest.raises(EdgarError, match="after 3 retries"):
        client.get("https://data.sec.gov/x")
    client404 = _client(lambda r: httpx.Response(404))
    with pytest.raises(EdgarError, match="404"):
        client404.get("https://data.sec.gov/x")
    assert client404.stats.requests == 1


def test_client_refuses_missing_user_agent_and_excess_rate() -> None:
    with pytest.raises(EdgarError, match="SEC_USER_AGENT"):
        EdgarClient("  ", 5)
    with pytest.raises(EdgarError, match="10 requests"):
        EdgarClient("A b@c.org", 10)


def _lock(data: bytes) -> Lockfile:
    entry = LockEntry(
        ticker="ACME", company="Acme", cik=1, form="10-K", fiscal_year=2025,
        period_of_report="2025-12-31", filing_date="2026-02-01",
        accession_number="0000000001-26-000001", primary_document="acme.htm",
        url="https://www.sec.gov/Archives/edgar/data/1/000000000126000001/acme.htm",
        local_path="ACME/ACME-10K-FY2025.htm", sha256=sha256_bytes(data), size_bytes=len(data),
    )  # fmt: skip
    return Lockfile(resolved_at="2026-11-17", form="10-K", filings_per_company=1, filings=[entry])


def test_download_skips_verified_files_and_detects_changes(tmp_path: Path) -> None:
    body = b"<html>filing</html>"
    lock = _lock(body)
    hits: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        hits.append(str(request.url))
        return httpx.Response(200, content=body)

    report = edgar.download(_client(handler), lock, tmp_path)
    assert report.downloaded == ["ACME/ACME-10K-FY2025.htm"]
    report = edgar.download(_client(handler), lock, tmp_path)
    assert report.skipped == ["ACME/ACME-10K-FY2025.htm"]
    assert len(hits) == 1

    (tmp_path / "ACME/ACME-10K-FY2025.htm").unlink()
    changed = _client(lambda r: httpx.Response(200, content=b"tampered"))
    with pytest.raises(EdgarError, match="SHA-256 mismatch"):
        edgar.download(changed, lock, tmp_path)


def test_lockfile_round_trip(tmp_path: Path) -> None:
    lock = _lock(b"x")
    path = tmp_path / "lock.json"
    path.write_text(lock.to_json())
    assert Lockfile.load(path) == lock
    assert json.loads(path.read_text())["filings"][0]["ticker"] == "ACME"


def test_committed_lockfile_has_three_original_10ks_per_company() -> None:
    from docqa.config import get_settings

    settings = get_settings()
    lock = Lockfile.load(settings.filings_lock_file)
    companies = edgar.load_companies(settings.companies_file)
    assert len(lock.filings) == 3 * len(companies) == 15
    for company in companies:
        entries = [f for f in lock.filings if f.ticker == company.ticker]
        assert len(entries) == 3
        assert all(f.form == "10-K" for f in entries)
        years = sorted(f.fiscal_year for f in entries)
        assert years == list(range(years[0], years[0] + 3))


@pytest.mark.parametrize("agent", ["", "Your Name your.email@example.com"])
def test_cli_refuses_placeholder_user_agent(monkeypatch: pytest.MonkeyPatch, agent: str) -> None:
    from docqa.cli import app
    from docqa.config import get_settings

    monkeypatch.setenv("SEC_USER_AGENT", agent)
    get_settings.cache_clear()
    try:
        result = CliRunner().invoke(app, ["download-edgar"])
    finally:
        get_settings.cache_clear()
    assert result.exit_code == 2
    assert "SEC_USER_AGENT" in result.output
