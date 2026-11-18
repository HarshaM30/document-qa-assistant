"""Cross-check numeric gold answers against SEC XBRL `companyfacts`.

For every numeric fact with an `xbrl_concept`, find the annual (or period-end) value that
the company reported for that fiscal year and compare it with the gold value. Facts without
a concept must carry an `xbrl_note` explaining why (e.g. a segment figure, which
companyfacts doesn't include). Responses are cached under RAW_DATA_DIR/xbrl.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from pathlib import Path
from typing import Any

from docqa.evals.dataset import Dataset, NumericFact
from docqa.ingestion.edgar import EdgarClient, LockEntry, Lockfile

# Multiplier from a gold unit to the XBRL base unit, and the XBRL unit key.
UNITS: dict[str, tuple[float, str | None]] = {
    "USD": (1, "USD"),
    "USD millions": (1e6, "USD"),
    "USD billions": (1e9, "USD"),
    "USD per share": (1, "USD/shares"),
    "shares": (1, "shares"),
    "shares millions": (1e6, "shares"),
    "percent": (1, None),
    "employees": (1, None),
}
MIN_ANNUAL_DAYS = 350


def companyfacts_url(cik: int) -> str:
    return f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"


def cached_companyfacts(client: EdgarClient, cache_dir: Path) -> Callable[[int], dict[str, Any]]:
    def fetch(cik: int) -> dict[str, Any]:
        path = cache_dir / f"CIK{cik:010d}.json"
        if path.exists():
            data: dict[str, Any] = json.loads(path.read_text())
            return data
        data = client.get_json(companyfacts_url(cik))
        cache_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data))
        return data

    return fetch


@dataclass(frozen=True)
class XbrlValue:
    value: float
    start: str | None
    end: str
    accession: str
    form: str


def _days(start: str, end: str) -> int:
    return (date.fromisoformat(end) - date.fromisoformat(start)).days


def find_value(
    facts: dict[str, Any], concept: str, unit: str, period_end: str, accession: str | None
) -> XbrlValue | None:
    """The annual (duration) or period-end (instant) value ending on `period_end`.

    Prefers the value from the given filing, then the most recently filed one.
    """
    taxonomy, _, name = concept.partition(":")
    entries = facts.get("facts", {}).get(taxonomy, {}).get(name, {}).get("units", {}).get(unit, [])
    matches = [
        e
        for e in entries
        if e.get("end") == period_end
        and str(e.get("form", "")).startswith("10-K")
        and ("start" not in e or _days(e["start"], e["end"]) >= MIN_ANNUAL_DAYS)
    ]
    if not matches:
        return None
    matches.sort(key=lambda e: (e.get("accn") == accession, e.get("filed", "")), reverse=True)
    best = matches[0]
    return XbrlValue(float(best["val"]), best.get("start"), best["end"], best["accn"], best["form"])


class Status(StrEnum):
    MATCH = "match"
    MISMATCH = "mismatch"
    MISSING = "missing"  # concept has no value for that period
    EXPLAINED = "explained"  # no concept, with a documented reason
    UNEXPLAINED = "unexplained"  # no concept and no reason


@dataclass(frozen=True)
class XbrlResult:
    item_id: str
    fact: NumericFact
    status: Status
    xbrl: XbrlValue | None = None
    detail: str = ""

    @property
    def needs_attention(self) -> bool:
        """Mismatches and missing values are acceptable only with a documented reason."""
        if self.status in (Status.MATCH, Status.EXPLAINED):
            return False
        return self.status == Status.UNEXPLAINED or not self.fact.xbrl_note


def values_agree(gold: float, scale: float, xbrl: float) -> bool:
    """Equal up to the gold value's rounding (half a unit of its scale) or 0.1%."""
    expected = gold * scale
    return abs(expected - xbrl) <= max(0.5 * scale, 0.001 * abs(xbrl))


def check_dataset(
    dataset: Dataset, lock: Lockfile, companyfacts: Callable[[int], dict[str, Any]]
) -> list[XbrlResult]:
    filings: dict[tuple[str, int], LockEntry] = {(e.ticker, e.fiscal_year): e for e in lock.filings}
    results = []
    for item in dataset.items:
        for fact in item.numeric:
            results.append(_check(item.id, fact, filings, companyfacts))
    return results


def _check(
    item_id: str,
    fact: NumericFact,
    filings: dict[tuple[str, int], LockEntry],
    companyfacts: Callable[[int], dict[str, Any]],
) -> XbrlResult:
    if not fact.xbrl_concept:
        status = Status.EXPLAINED if fact.xbrl_note else Status.UNEXPLAINED
        return XbrlResult(item_id, fact, status, detail=fact.xbrl_note or "no concept or note")
    if fact.unit not in UNITS or UNITS[fact.unit][1] is None:
        return XbrlResult(
            item_id, fact, Status.UNEXPLAINED, detail=f"unit {fact.unit!r} not in XBRL"
        )
    entry = filings.get((fact.company, fact.fiscal_year))
    if entry is None:
        return XbrlResult(
            item_id, fact, Status.MISSING, detail=f"no locked filing for FY{fact.fiscal_year}"
        )
    scale, unit = UNITS[fact.unit]
    assert unit is not None
    value = find_value(
        companyfacts(entry.cik),
        fact.xbrl_concept,
        unit,
        entry.period_of_report,
        entry.accession_number,
    )
    if value is None:
        return XbrlResult(
            item_id,
            fact,
            Status.MISSING,
            detail=f"no {fact.xbrl_concept} value ending {entry.period_of_report}",
        )
    status = Status.MATCH if values_agree(fact.value, scale, value.value) else Status.MISMATCH
    return XbrlResult(item_id, fact, status, value)
