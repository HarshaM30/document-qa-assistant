from __future__ import annotations

import itertools

import pytest

from docqa.ingestion.chunking import ChunkingConfig, NaiveChunker, SectionChunker
from docqa.ingestion.html_blocks import Cell, TableBlock, TextBlock
from docqa.ingestion.parsed import ParsedDocument, ParsedSection
from tests.unit.fakes import WhitespaceTokenizer

TOK = WhitespaceTokenizer()


def sentence(i: int, words: int = 9) -> str:
    return " ".join([f"S{i}w{j}" for j in range(words - 1)] + [f"end{i}."])


def doc_with(*sections: ParsedSection) -> ParsedDocument:
    return ParsedDocument(sections=list(sections), page_count=3)


def test_config_key_and_validation() -> None:
    assert ChunkingConfig("section", 512, 64).key == "section-512-64"
    with pytest.raises(ValueError, match="overlap"):
        ChunkingConfig("section", 100, 100)


def test_chunks_respect_size_and_section_boundaries() -> None:
    para = " ".join(sentence(i) for i in range(30))  # 270 words
    doc = doc_with(
        ParsedSection("1", "Item 1. Business", [TextBlock(para, 1)]),
        ParsedSection("1A", "Item 1A. Risk Factors", [TextBlock("Risk one. Risk two.", 2)]),
    )
    chunks = SectionChunker(TOK, ChunkingConfig("section", 64, 10)).chunk(doc, "ACME 10-K FY2025")
    first_section = [c for c in chunks if c.section_index == 0]
    assert len(first_section) > 3
    heading_tokens = TOK.count_batch(["ACME 10-K FY2025 — Item 1. Business"])[0]
    assert all(c.token_count <= 64 - heading_tokens - 2 for c in first_section)
    last = chunks[-1]
    assert last.section_index == 1
    assert last.text == "Risk one. Risk two."
    assert last.heading == "ACME 10-K FY2025 — Item 1A. Risk Factors"
    assert last.page_start == 2


def test_overlap_carries_trailing_sentences() -> None:
    para = " ".join(sentence(i) for i in range(12))
    doc = doc_with(ParsedSection(None, "Page 1", [TextBlock(para, 1)]))
    chunks = SectionChunker(TOK, ChunkingConfig("section", 40, 10)).chunk(doc, "")
    for prev, nxt in itertools.pairwise(chunks):
        last_sentence = prev.text.split(". ")[-1]
        assert nxt.text.startswith(last_sentence.rstrip("."))


def test_no_overlap_when_disabled() -> None:
    para = " ".join(sentence(i) for i in range(12))
    doc = doc_with(ParsedSection(None, "Page 1", [TextBlock(para, 1)]))
    chunks = SectionChunker(TOK, ChunkingConfig("section", 40, 0)).chunk(doc, "")
    words = [w for c in chunks for w in c.text.split()]
    assert len(words) == len(set(words)) == 108


def test_oversized_sentence_is_split() -> None:
    doc = doc_with(ParsedSection(None, "Page 1", [TextBlock(" ".join(["w"] * 200), 1)]))
    chunks = SectionChunker(TOK, ChunkingConfig("section", 50, 0)).chunk(doc, "")
    assert sum(c.token_count for c in chunks) == 200
    assert max(c.token_count for c in chunks) <= 48


def test_data_table_is_standalone_and_split_between_rows() -> None:
    rows = [[Cell(""), Cell("2025"), Cell("2024")]]
    rows += [[Cell(f"Line item {i}"), Cell(f"{i},000"), Cell(f"{i},500")] for i in range(20)]
    section = ParsedSection(
        "7",
        "Item 7. MD&A",
        [
            TextBlock("Revenue grew.", 3),
            TableBlock(rows, page=3, caption="Revenue (in millions):"),
            TextBlock("After the table.", 4),
        ],
    )
    chunks = SectionChunker(TOK, ChunkingConfig("section", 60, 0)).chunk(doc_with(section), "")
    kinds = [c.is_table for c in chunks]
    assert kinds[0] is False
    assert kinds[-1] is False
    tables = [c for c in chunks if c.is_table]
    assert len(tables) > 1
    for t in tables:
        lines = t.text.splitlines()
        assert lines[:2] == ["Table: Revenue (in millions):", "Units: in millions"]
        assert all(ln.startswith("Line item ") and ln.endswith("500") for ln in lines[2:])
    all_rows = [ln for t in tables for ln in t.text.splitlines()[2:]]
    assert len(all_rows) == 20
    assert chunks[0].text == "Revenue grew."
    assert chunks[-1].text == "After the table."


def test_naive_chunker_windows_and_attribution() -> None:
    doc = doc_with(
        ParsedSection(None, "Page 1", [TextBlock(" ".join(f"a{i}" for i in range(50)), 1)]),
        ParsedSection(None, "Page 2", [TextBlock(" ".join(f"b{i}" for i in range(50)), 2)]),
    )
    chunks = NaiveChunker(TOK, ChunkingConfig("naive", 42, 8)).chunk(doc, "")
    assert all(c.token_count <= 40 for c in chunks)
    assert chunks[0].section_index == 0
    assert chunks[0].page_start == 1
    assert chunks[-1].section_index == 1
    assert chunks[-1].page_end == 2
    spanning = [c for c in chunks if "a49" in c.text and "b0" in c.text]
    assert spanning
    assert spanning[0].page_start == 1
    assert spanning[0].page_end == 2
    assert chunks[1].text.split()[0] == chunks[0].text.split()[-8]  # 8-token overlap


def test_context_config_keys() -> None:
    assert ChunkingConfig("section", 512, 64, "tables").key == "section-512-64-ctx-tables"
    assert ChunkingConfig("section", 512, 64, "all").key == "section-512-64-ctx-all"
    with pytest.raises(ValueError, match="naive"):
        ChunkingConfig("naive", 512, 64, "tables")


def _financial_section() -> ParsedSection:
    rows = [[Cell(""), Cell("2025"), Cell("2024")]]
    rows += [[Cell(f"Line item {i}"), Cell(f"{i},000"), Cell(f"{i},500")] for i in range(3)]
    return ParsedSection(
        "7",
        "Item 7. Management's Discussion and Analysis of Financial Condition",
        [
            TextBlock("Segment Operating Performance", 3),
            TextBlock("The following table shows net sales by segment (in millions):", 3),
            TableBlock(rows, page=3, caption="The following table shows net sales by segment"),
            TextBlock("Revenue grew.", 3),
            TableBlock(rows, page=3, caption="(a) Excludes amounts that are not allocated."),
        ],
    )


@pytest.mark.parametrize("context", ["tables", "all"])
def test_short_context_header_on_tables(context: str) -> None:
    config = ChunkingConfig("section", 200, 0, context)  # type: ignore[arg-type]
    chunks = SectionChunker(TOK, config).chunk(doc_with(_financial_section()), "ACME 10-K FY2025")
    tables = [c for c in chunks if c.is_table]
    # Nearest sub-heading within a few blocks is the title; footnote captions are not.
    assert [t.heading for t in tables] == [
        "ACME 10-K FY2025 | Item 7 MD&A | Segment Operating Performance",
        "ACME 10-K FY2025 | Item 7 MD&A | Segment Operating Performance",
    ]
    # The stored text is unchanged, so quotes and citations still match it.
    assert tables[0].text.splitlines()[0].startswith("Table: The following table")
    text_heading = next(c.heading for c in chunks if not c.is_table)
    if context == "all":
        assert text_heading == "ACME 10-K FY2025 | Item 7 MD&A"
    else:
        assert text_heading.startswith("ACME 10-K FY2025 — Item 7. Management's")


def test_table_title_falls_back_to_short_caption() -> None:
    rows = [[Cell(""), Cell("2025")], [Cell("A"), Cell("1")], [Cell("B"), Cell("2")]]
    long_caption = "The following table summarizes the activity " + "in the account " * 6
    section = ParsedSection(
        "8",
        "Item 8. Financial Statements",
        [
            TextBlock("Revenue grew strongly in the year.", 1),
            TableBlock(rows, page=1, caption=long_caption),
        ],
    )
    config = ChunkingConfig("section", 200, 0, "tables")
    [table] = [c for c in SectionChunker(TOK, config).chunk(doc_with(section), "X") if c.is_table]
    title = table.heading.split(" | ")[-1]
    assert title.startswith("The following table summarizes")
    assert title.endswith("…")
    assert len(title) <= 81
