from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest
from pydantic import ValidationError

from docqa.evals.dataset import (
    DEFAULT_DATASET,
    Category,
    QAItem,
    Source,
    contains_quote,
    contains_quote_tokens,
    gold_chunk_ids,
    load_dataset,
    normalize,
    verify_quotes,
)


def _item(**kw: object) -> QAItem:
    base: dict[str, object] = {
        "id": "T1",
        "category": "table",
        "question": "q?",
        "gold_answer": "a",
        "answerable": True,
        "companies": ["ACME"],
        "fiscal_years": [2025],
        "sources": [
            {"doc": "ACME-FY2025", "section": "7", "quote": "Total net sales | 2025: $100"}
        ],
    }
    return QAItem.model_validate(base | kw)


def test_normalize_ignores_case_whitespace_and_quote_style() -> None:
    curly = f"The  Company{chr(0x2019)}s\n{chr(0x201C)}fiscal{chr(0x201D)} year"
    assert normalize(curly) == 'the company\'s "fiscal" year'
    assert contains_quote(f"Net   sales rose{chr(0x2014)}sharply.", "net sales rose-sharply")


def test_token_fallback_matches_unlabelled_table_text() -> None:
    naive = "Total net sales $ 1,200 $ 1,000 Cost of sales 2025 2024"
    assert not contains_quote(naive, "Total net sales | 2025: $1,200")
    assert contains_quote_tokens(naive, "Total net sales | 2025: $1,200")
    assert not contains_quote_tokens(naive, "Total net sales | 2025: $1,300")


def test_gold_chunks_prefer_exact_matches() -> None:
    quote = "Total net sales | 2025: $1,200"
    chunks = [
        ("a", "Total net sales | 2025: $1,200 | 2024: $1,000"),
        ("b", "total net sales 2025 1,200 (repeated in a summary)"),
        ("c", "unrelated"),
    ]
    assert gold_chunk_ids(quote, chunks) == ["a"]
    assert gold_chunk_ids(quote, chunks[1:]) == ["b"]
    assert gold_chunk_ids(quote, chunks[2:]) == []


def test_item_validation() -> None:
    assert _item().sources[0].ticker == "ACME"
    with pytest.raises(ValidationError, match="answerable must be false"):
        _item(category="unanswerable")
    with pytest.raises(ValidationError, match="need at least one source"):
        _item(sources=[])
    with pytest.raises(ValidationError, match="carry no sources"):
        _item(category="unanswerable", answerable=False)
    with pytest.raises(ValidationError):
        Source(doc="acme-2025", section="7", quote="long enough quote")


def test_load_rejects_duplicate_ids(tmp_path: Path) -> None:
    line = _item().model_dump_json()
    path = tmp_path / "d.jsonl"
    path.write_text(line + "\n" + line + "\n")
    with pytest.raises(ValueError, match="duplicate"):
        load_dataset(path)


def test_verify_quotes_checks_the_stated_section() -> None:
    item = _item()
    filings = {"ACME-FY2025": [("7", "MD&A", "Total net sales | 2025: $100 | 2024: $90")]}
    assert verify_quotes([item], filings)[0].ok
    moved = {"ACME-FY2025": [("8", "Statements", "Total net sales | 2025: $100")]}
    check = verify_quotes([item], moved)[0]
    assert not check.ok
    assert check.found_elsewhere == ["8"]
    assert verify_quotes([item], {})[0].found_elsewhere == ["<filing not found>"]


def test_committed_dataset_shape() -> None:
    ds = load_dataset(DEFAULT_DATASET)
    assert len(ds.items) == 50
    counts = Counter(i.category for i in ds.items)
    assert counts == {
        Category.FACTUAL: 12,
        Category.TABLE: 12,
        Category.YOY: 8,
        Category.CROSS_COMPANY: 8,
        Category.UNANSWERABLE: 10,
    }
    assert ds.version.startswith("qa_v1@")
    lock = json.loads((DEFAULT_DATASET.parents[2] / "data" / "filings.lock.json").read_text())
    filed = {(f["ticker"], f["fiscal_year"]) for f in lock["filings"]}
    for item in ds.items:
        for source in item.sources:
            assert (source.ticker, source.fiscal_year) in filed, item.id
        for fact in item.numeric:
            assert fact.xbrl_concept or fact.xbrl_note, item.id
        if item.category == Category.CROSS_COMPANY:
            # Only fiscal years every compared company has filed.
            assert all((c, y) in filed for c in item.companies for y in item.fiscal_years)
