from __future__ import annotations

from pathlib import Path

import pytest

from docqa.ingestion.html_10k import parse_10k, select_headings
from docqa.ingestion.html_blocks import TableBlock, TextBlock, extract_blocks
from docqa.ingestion.parsed import ParsedDocument
from docqa.ingestion.tables import render_table

FIXTURE = Path(__file__).parents[1] / "fixtures" / "sample_10k.htm"


@pytest.fixture(scope="module")
def parsed() -> ParsedDocument:
    return parse_10k(FIXTURE.read_bytes())


def _text(doc: ParsedDocument, code: str) -> str:
    section = doc.item(code)
    assert section is not None
    return "\n".join(b.text for b in section.blocks)


def test_item_boundaries(parsed: ParsedDocument) -> None:
    assert parsed.item_codes == ["1", "1A", "1B", "7", "7A", "8", "15"]
    assert _text(parsed, "1").startswith("Northwind Outdoor Co. (the “Company”) designs")
    assert "Portugal" in _text(parsed, "1A")
    assert "Portugal" not in _text(parsed, "1")
    assert _text(parsed, "1B") == "None."
    assert "foreign currency risk" in _text(parsed, "7A")
    assert "foreign currency risk" not in _text(parsed, "7")


def test_titles_normalized(parsed: ParsedDocument) -> None:
    item7 = parsed.item("7")
    assert item7 is not None
    assert item7.title == (
        "Item 7. Management\u2019s Discussion and Analysis of Financial Condition "
        "and Results of Operations"
    )
    assert parsed.item("1") is not None
    assert parsed.item("1").title == "Item 1. Business"  # type: ignore[union-attr]


def test_table_of_contents_ignored(parsed: ParsedDocument) -> None:
    cover = parsed.sections[0]
    assert cover.item_code is None
    assert any("Item 1A. Risk Factors 3" in b.text for b in cover.blocks)
    # The TOC lines did not become section starts.
    assert len(parsed.sections) == len(parsed.item_codes) + 1


def test_cross_reference_sentence_is_not_a_heading(parsed: ParsedDocument) -> None:
    assert parsed.item_codes.count("7") == 1
    assert "See Item 7 of this Form 10-K" in _text(parsed, "1A")


def test_hidden_xbrl_and_running_footers_removed(parsed: ParsedDocument) -> None:
    all_text = "\n".join(b.text for s in parsed.sections for b in s.blocks)
    assert "HIDDEN XBRL CONTEXT" not in all_text
    assert all_text.count("2025 Form 10-K |") == 1  # only the first footer survives
    assert "PART II" not in all_text


def test_page_numbers_follow_page_breaks(parsed: ParsedDocument) -> None:
    assert parsed.page_count == 5
    item1, item7, item15 = parsed.item("1"), parsed.item("7"), parsed.item("15")
    assert item1 is not None
    assert item7 is not None
    assert item15 is not None
    assert (item1.page_start, item7.page_start, item15.page_start) == (2, 3, 5)


def test_segment_table_rendered_with_labels_and_units(parsed: ParsedDocument) -> None:
    item7 = parsed.item("7")
    assert item7 is not None
    table = next(b for b in item7.blocks if isinstance(b, TableBlock))
    rendered = render_table(table.rows, table.caption)
    assert rendered.is_data
    assert "Units: dollars in millions" in rendered.header
    assert rendered.rows == [
        "Americas | 2025: $12,400 | Change: 7% | 2024: $11,589",
        "Europe | 2025: 8,300 | Change: (4)% | 2024: 8,646",
        "Total net sales | 2025: $20,700 | Change: 9% | 2024: $20,235",
    ]


def test_income_statement_multirow_header_and_groups(parsed: ParsedDocument) -> None:
    item8 = parsed.item("8")
    assert item8 is not None
    table = next(b for b in item8.blocks if isinstance(b, TableBlock))
    rendered = render_table(table.rows, table.caption)
    assert rendered.header == [
        "Table: CONSOLIDATED STATEMENTS OF OPERATIONS",
        "Units: In millions, except per-share amounts",
    ]
    assert rendered.rows[0] == (
        "Net sales > Footwear | Years ended December 31, 2025: $12,400 "
        "| Years ended December 31, 2024: $11,589"
    )
    assert any(
        r.startswith("Other income (expense), net |") and "(152)" in r for r in rendered.rows
    )
    # The "Total net sales" row closes the "Net sales" group.
    assert any(r.startswith("Net income |") for r in rendered.rows)


def test_heading_split_across_spans_detected() -> None:
    blocks, _ = extract_blocks(
        b"<html><body><p><span>Item 7.</span><span> Management's Discussion</span></p>"
        b"<p>" + b"MD&A body text. " * 50 + b"</p></body></html>"
    )
    assert isinstance(blocks[0], TextBlock)
    assert [h.code for h in select_headings(blocks)] == ["7"]


def test_bare_running_header_is_not_a_heading() -> None:
    blocks, _ = extract_blocks(b"<html><body><p>Item 1</p><p>Some text.</p></body></html>")
    assert select_headings(blocks) == []
