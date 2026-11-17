"""SEC EDGAR client and 10-K downloader.

Follows SEC fair-access rules: every request carries a descriptive User-Agent, requests are
spaced by a token bucket kept below SEC's 10 requests/second, and 429/5xx responses are
retried with exponential backoff (honoring Retry-After).

Two modes:
- resolve: read each company's submissions index, pick the most recent original 10-Ks
  (10-K/A excluded), download them, and pin the result in `filings.lock.json`.
- download: fetch exactly what the lockfile lists and verify SHA-256s; existing files that
  already match are skipped.
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from collections.abc import Callable, Iterator
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import yaml

log = logging.getLogger(__name__)

SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
SUBMISSIONS_PAGE_URL = "https://data.sec.gov/submissions/{name}"
ARCHIVE_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{accession_nodash}/{document}"

RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})


class EdgarError(RuntimeError):
    pass


class TokenBucket:
    """Blocking token bucket. With capacity 1 it enforces even spacing of 1/rate seconds."""

    def __init__(
        self,
        rate_per_second: float,
        capacity: float = 1.0,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if rate_per_second <= 0:
            raise ValueError("rate_per_second must be positive")
        self.rate = rate_per_second
        self.capacity = capacity
        self._tokens = capacity
        self._clock = clock
        self._sleep = sleep
        self._last = clock()
        self._lock = threading.Lock()

    def acquire(self) -> None:
        with self._lock:
            while True:
                now = self._clock()
                self._tokens = min(self.capacity, self._tokens + (now - self._last) * self.rate)
                self._last = now
                if self._tokens >= 1 - 1e-9:  # tolerate float rounding
                    self._tokens -= 1
                    return
                self._sleep((1 - self._tokens) / self.rate)


@dataclass
class RequestStats:
    requests: int = 0
    retries: int = 0
    started: float = field(default_factory=time.monotonic)

    def rate(self) -> float:
        elapsed = time.monotonic() - self.started
        return self.requests / elapsed if elapsed > 0 else 0.0


class EdgarClient:
    def __init__(
        self,
        user_agent: str,
        max_requests_per_second: float,
        *,
        http: httpx.Client | None = None,
        max_retries: int = 5,
        backoff_base_seconds: float = 1.0,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if not user_agent.strip():
            raise EdgarError("SEC_USER_AGENT is required by SEC fair-access rules")
        if max_requests_per_second >= 10:
            raise EdgarError("SEC allows at most 10 requests/second; configure a lower rate")
        self.user_agent = user_agent
        self._http = http or httpx.Client(timeout=60, follow_redirects=True)
        self._http.headers.update({"User-Agent": user_agent, "Accept-Encoding": "gzip, deflate"})
        self._bucket = TokenBucket(max_requests_per_second)  # `sleep` is for backoff only
        self._max_retries = max_retries
        self._backoff = backoff_base_seconds
        self._sleep = sleep
        self.stats = RequestStats()

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> EdgarClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def get(self, url: str) -> httpx.Response:
        for attempt in range(self._max_retries + 1):
            self._bucket.acquire()
            self.stats.requests += 1
            try:
                response = self._http.get(url)
            except httpx.TransportError as exc:
                if attempt == self._max_retries:
                    raise EdgarError(f"GET {url} failed: {exc}") from exc
                delay = self._backoff * 2**attempt
            else:
                if response.status_code not in RETRY_STATUSES:
                    if response.is_error:
                        raise EdgarError(f"GET {url} returned HTTP {response.status_code}")
                    return response
                if attempt == self._max_retries:
                    raise EdgarError(
                        f"GET {url} returned HTTP {response.status_code} "
                        f"after {self._max_retries} retries"
                    )
                delay = _retry_after_seconds(response) or self._backoff * 2**attempt
            self.stats.retries += 1
            log.warning("retrying %s in %.1fs (attempt %d)", url, delay, attempt + 1)
            self._sleep(delay)
        raise AssertionError("unreachable")

    def get_json(self, url: str) -> dict[str, Any]:
        data: dict[str, Any] = self.get(url).json()
        return data


def _retry_after_seconds(response: httpx.Response) -> float | None:
    value = response.headers.get("Retry-After")
    if value is None:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        return None


# --- Companies and filing selection -------------------------------------------------------


@dataclass(frozen=True)
class Company:
    ticker: str
    name: str
    cik: int


def load_companies(path: Path) -> list[Company]:
    raw = yaml.safe_load(path.read_text())
    return [
        Company(ticker=c["ticker"], name=c["name"], cik=int(c["cik"])) for c in raw["companies"]
    ]


@dataclass(frozen=True)
class FilingRef:
    accession_number: str
    form: str
    filing_date: str
    period_of_report: str
    primary_document: str


def _rows(block: dict[str, Any]) -> Iterator[FilingRef]:
    for acc, form, filed, period, doc in zip(
        block["accessionNumber"],
        block["form"],
        block["filingDate"],
        block["reportDate"],
        block["primaryDocument"],
        strict=True,
    ):
        yield FilingRef(acc, form, filed, period, doc)


def select_filings(
    blocks: Iterator[dict[str, Any]] | list[dict[str, Any]], form: str, count: int
) -> list[FilingRef]:
    """Pick the `count` most recent filings of exactly `form` (amendments like 10-K/A excluded).

    `blocks` are the column-oriented filing tables from the submissions API, newest first;
    they are consumed lazily so older pages are only fetched when needed.
    """
    found: list[FilingRef] = []
    for block in blocks:
        found.extend(r for r in _rows(block) if r.form == form and r.primary_document)
        if len(found) >= count:
            break
    found.sort(key=lambda r: r.filing_date, reverse=True)
    return found[:count]


def iter_submission_blocks(client: EdgarClient, cik: int) -> Iterator[dict[str, Any]]:
    """Yield the recent-filings table, then older pages, for one company."""
    data = client.get_json(SUBMISSIONS_URL.format(cik=cik))
    yield data["filings"]["recent"]
    for page in data["filings"].get("files", []):
        yield client.get_json(SUBMISSIONS_PAGE_URL.format(name=page["name"]))


def archive_url(cik: int, accession_number: str, document: str) -> str:
    return ARCHIVE_URL.format(
        cik=cik, accession_nodash=accession_number.replace("-", ""), document=document
    )


# --- Lockfile ------------------------------------------------------------------------------


@dataclass
class LockEntry:
    ticker: str
    company: str
    cik: int
    form: str
    fiscal_year: int
    period_of_report: str
    filing_date: str
    accession_number: str
    primary_document: str
    url: str
    local_path: str
    sha256: str
    size_bytes: int


@dataclass
class Lockfile:
    resolved_at: str
    form: str
    filings_per_company: int
    filings: list[LockEntry]

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2) + "\n"

    @classmethod
    def load(cls, path: Path) -> Lockfile:
        raw = json.loads(path.read_text())
        return cls(
            resolved_at=raw["resolved_at"],
            form=raw["form"],
            filings_per_company=raw["filings_per_company"],
            filings=[LockEntry(**f) for f in raw["filings"]],
        )


def fiscal_year_of(period_of_report: str) -> int:
    """Fiscal year = calendar year in which the fiscal period ends (e.g. Apple Sept 2026 → 2026)."""
    return int(period_of_report[:4])


def local_name(ticker: str, fiscal_year: int, primary_document: str) -> str:
    suffix = Path(primary_document).suffix or ".htm"
    return f"{ticker}/{ticker}-10K-FY{fiscal_year}{suffix}"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


# --- Resolve and download ------------------------------------------------------------------


@dataclass
class DownloadReport:
    downloaded: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)


def _write_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".part")
    tmp.write_bytes(data)
    tmp.replace(path)


def resolve(
    client: EdgarClient,
    companies: list[Company],
    raw_dir: Path,
    *,
    form: str = "10-K",
    per_company: int = 3,
) -> Lockfile:
    """Find the latest filings for each company, download them, and build a lockfile."""
    entries: list[LockEntry] = []
    for company in companies:
        refs = select_filings(iter_submission_blocks(client, company.cik), form, per_company)
        if len(refs) < per_company:
            raise EdgarError(f"{company.ticker}: found only {len(refs)} {form} filings")
        for ref in refs:
            fy = fiscal_year_of(ref.period_of_report)
            url = archive_url(company.cik, ref.accession_number, ref.primary_document)
            rel = local_name(company.ticker, fy, ref.primary_document)
            data = client.get(url).content
            _write_atomic(raw_dir / rel, data)
            log.info(
                "resolved %s FY%d %s (%d bytes)",
                company.ticker,
                fy,
                ref.accession_number,
                len(data),
            )
            entries.append(
                LockEntry(
                    ticker=company.ticker,
                    company=company.name,
                    cik=company.cik,
                    form=ref.form,
                    fiscal_year=fy,
                    period_of_report=ref.period_of_report,
                    filing_date=ref.filing_date,
                    accession_number=ref.accession_number,
                    primary_document=ref.primary_document,
                    url=url,
                    local_path=rel,
                    sha256=sha256_bytes(data),
                    size_bytes=len(data),
                )
            )
    return Lockfile(
        resolved_at=datetime.now(UTC).date().isoformat(),
        form=form,
        filings_per_company=per_company,
        filings=entries,
    )


def download(client: EdgarClient, lock: Lockfile, raw_dir: Path) -> DownloadReport:
    """Download every locked filing that isn't already present with the right SHA-256."""
    report = DownloadReport()
    for entry in lock.filings:
        path = raw_dir / entry.local_path
        if path.exists() and sha256_file(path) == entry.sha256:
            report.skipped.append(entry.local_path)
            continue
        data = client.get(entry.url).content
        actual = sha256_bytes(data)
        if actual != entry.sha256:
            raise EdgarError(
                f"{entry.local_path}: SHA-256 mismatch (expected {entry.sha256}, got {actual}). "
                "The filing on EDGAR changed; re-resolve with --resolve."
            )
        _write_atomic(path, data)
        report.downloaded.append(entry.local_path)
        log.info("downloaded %s (%d bytes)", entry.local_path, len(data))
    return report


def write_manifest(lock: Lockfile, raw_dir: Path) -> Path:
    """Record what is on disk (path, size, SHA-256) next to the raw files."""
    files = []
    for entry in lock.filings:
        path = raw_dir / entry.local_path
        files.append(
            {
                "path": entry.local_path,
                "accession_number": entry.accession_number,
                "url": entry.url,
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    manifest = raw_dir / "manifest.json"
    manifest.write_text(
        json.dumps(
            {"generated_at": datetime.now(UTC).isoformat(timespec="seconds"), "files": files},
            indent=2,
        )
        + "\n"
    )
    return manifest
