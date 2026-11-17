from __future__ import annotations

from pathlib import Path

import pytest

from docqa.ingestion.html_blocks import TableBlock
from docqa.ingestion.parsed import DocumentParseError
from docqa.ingestion.pdf import parse_pdf
from docqa.ingestion.tables import render_table

FIXTURE = Path(__file__).parents[1] / "fixtures" / "sample_report.pdf"


def test_pages_become_sections_with_page_numbers() -> None:
    doc = parse_pdf(FIXTURE)
    assert doc.page_count == 3
    assert [s.title for s in doc.sections] == ["Page 1", "Page 2", "Page 3"]
    assert all(b.page == i + 1 for i, s in enumerate(doc.sections) for b in s.blocks)
    assert "Portugal" in " ".join(b.text for b in doc.sections[2].blocks)


def test_ruled_table_extracted_once_and_rendered() -> None:
    page2 = parse_pdf(FIXTURE).sections[1]
    tables = [b for b in page2.blocks if isinstance(b, TableBlock)]
    assert len(tables) == 1
    rendered = render_table(tables[0].rows, tables[0].caption)
    assert "Total revenue | 2025: 20,700 | 2024: 18,950" in rendered.rows
    assert "Units: in thousands" in rendered.header
    # Table cells are not duplicated in the page's running text.
    text_blocks = [b.text for b in page2.blocks if not isinstance(b, TableBlock)]
    assert not any("20,700" in t for t in text_blocks)


def test_corrupt_pdf_raises_readable_error(tmp_path: Path) -> None:
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"%PDF-1.4\nthis is not really a pdf")
    with pytest.raises(DocumentParseError, match="could not be read"):
        parse_pdf(bad)
