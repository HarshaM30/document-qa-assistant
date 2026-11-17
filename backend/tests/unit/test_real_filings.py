"""Every locked 10-K parses with the core Items. Skipped when data/raw hasn't been downloaded."""

from __future__ import annotations

import pytest

from docqa.config import get_settings
from docqa.ingestion.edgar import Lockfile
from docqa.ingestion.html_10k import parse_10k

_settings = get_settings()
_lock = Lockfile.load(_settings.filings_lock_file)
_entries = [e for e in _lock.filings if (_settings.raw_data_dir / e.local_path).exists()]

pytestmark = pytest.mark.skipif(not _entries, reason="filings not downloaded (run `make download`)")

REQUIRED = ["1", "1A", "7", "8"]
MIN_CHARS = {"1": 5_000, "1A": 20_000, "7": 10_000, "8": 40_000}


@pytest.mark.parametrize("entry", _entries, ids=lambda e: e.local_path.split("/")[-1])
def test_filing_has_core_items(entry: object) -> None:
    from docqa.ingestion.edgar import LockEntry

    assert isinstance(entry, LockEntry)
    doc = parse_10k((_settings.raw_data_dir / entry.local_path).read_bytes())
    for code in REQUIRED:
        section = doc.item(code)
        assert section is not None, f"Item {code} not found"
        assert section.char_count >= MIN_CHARS[code], f"Item {code} is suspiciously short"
    codes = doc.item_codes
    assert codes == sorted(codes, key=["1", "1A", "1B", "1C", "2", "3", "4", "5", "6", "7",
                                       "7A", "8", "9", "9A", "9B", "9C", "10", "11", "12", "13",
                                       "14", "15", "16"].index)  # fmt: skip
