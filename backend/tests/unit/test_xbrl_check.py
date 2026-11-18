from __future__ import annotations

from pathlib import Path
from typing import Any

from docqa.evals.dataset import Dataset, QAItem
from docqa.evals.xbrl_check import Status, check_dataset, find_value, values_agree
from docqa.ingestion.edgar import LockEntry, Lockfile

FACTS: dict[str, Any] = {
    "facts": {
        "us-gaap": {
            "Revenues": {
                "units": {
                    "USD": [
                        # quarterly value with the same end date: ignored
                        {"start": "2025-07-01", "end": "2025-09-30", "val": 30e9,
                         "accn": "A2", "form": "10-K", "filed": "2025-11-01"},
                        {"start": "2024-10-01", "end": "2025-09-30", "val": 101e9,
                         "accn": "A2", "form": "10-K", "filed": "2025-11-01"},
                        # restated in a later filing
                        {"start": "2024-10-01", "end": "2025-09-30", "val": 102e9,
                         "accn": "A3", "form": "10-K", "filed": "2026-11-01"},
                    ]
                }
            },
            "Assets": {"units": {"USD": [
                {"end": "2025-09-30", "val": 5e11, "accn": "A2", "form": "10-K", "filed": "x"},
            ]}},
        }
    }
}  # fmt: skip


def _entry() -> LockEntry:
    return LockEntry(
        ticker="ACME", company="Acme", cik=1, form="10-K", fiscal_year=2025,
        period_of_report="2025-09-30", filing_date="2025-11-01", accession_number="A2",
        primary_document="a.htm", url="u", local_path="p", sha256="0", size_bytes=1,
    )  # fmt: skip


def test_find_value_prefers_annual_value_from_the_same_filing() -> None:
    v = find_value(FACTS, "us-gaap:Revenues", "USD", "2025-09-30", "A2")
    assert v is not None
    assert v.value == 101e9
    later = find_value(FACTS, "us-gaap:Revenues", "USD", "2025-09-30", None)
    assert later is not None
    assert later.value == 102e9
    assert find_value(FACTS, "us-gaap:Assets", "USD", "2025-09-30", "A2") is not None
    assert find_value(FACTS, "us-gaap:Missing", "USD", "2025-09-30", "A2") is None


def test_values_agree_within_rounding() -> None:
    assert values_agree(101_000, 1e6, 101_000_400_000)
    assert not values_agree(101_000, 1e6, 101_600_000_000)
    assert values_agree(8.98, 1, 8.98)


def test_check_dataset_statuses() -> None:
    def item(id_: str, numeric: list[dict[str, Any]]) -> QAItem:
        return QAItem.model_validate({
            "id": id_, "category": "table", "question": "q", "gold_answer": "a",
            "answerable": True, "companies": ["ACME"], "fiscal_years": [2025],
            "sources": [{"doc": "ACME-FY2025", "section": "8", "quote": "long enough quote"}],
            "numeric": numeric,
        })  # fmt: skip

    fact = {"unit": "USD millions", "company": "ACME", "fiscal_year": 2025}
    ds = Dataset(Path("d.jsonl"), [
        item("ok", [fact | {"value": 101_000, "xbrl_concept": "us-gaap:Revenues"}]),
        item("bad", [fact | {"value": 99_000, "xbrl_concept": "us-gaap:Revenues"}]),
        item("seg", [fact | {"value": 5, "xbrl_note": "segment figure"}]),
        item("bare", [fact | {"value": 5}]),
        item("old", [fact | {"value": 5, "fiscal_year": 2019, "xbrl_concept": "us-gaap:Revenues"}]),
    ])  # fmt: skip
    results = {
        r.item_id: r
        for r in check_dataset(ds, Lockfile("x", "10-K", 1, [_entry()]), lambda cik: FACTS)
    }
    assert results["ok"].status == Status.MATCH
    assert not results["ok"].needs_attention
    assert results["bad"].status == Status.MISMATCH
    assert results["bad"].needs_attention
    assert results["seg"].status == Status.EXPLAINED
    assert not results["seg"].needs_attention
    assert results["bare"].status == Status.UNEXPLAINED
    assert results["bare"].needs_attention
    assert results["old"].status == Status.MISSING
