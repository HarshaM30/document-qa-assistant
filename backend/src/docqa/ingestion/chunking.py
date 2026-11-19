"""Chunkers: section/table-aware (the default) and naive fixed-size windows (for ablations).

Sizes are measured in tokens of the embedding model's tokenizer, so a 512-token chunk
fits the model's context exactly.

Section-aware chunking
- never crosses a section (10-K Item or PDF page) boundary;
- packs whole sentences, carrying up to `overlap` tokens of trailing sentences forward;
- emits each data table as its own chunk(s), split between rows only, with the caption
  and units repeated on every part.

Chunk headings (embedded together with the text, and shown to the model as the source line)
come in two styles, chosen by `ChunkingConfig.context`:
- "heading": the document label plus the full section title, e.g.
  "Apple Inc. 10-K FY2026 — Item 7. Management's Discussion and Analysis of ...";
- a short context header, e.g. "Apple Inc. 10-K FY2026 | Item 7 MD&A | Segment Operating
  Performance", with the table's title (its nearest sub-heading, else its caption). The
  header goes on table chunks only ("tables") or on every chunk ("all").
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal, Protocol

from docqa.ingestion.html_10k import ITEM_SHORT_NAMES
from docqa.ingestion.html_blocks import Block, TableBlock, TextBlock
from docqa.ingestion.parsed import ParsedDocument, ParsedSection
from docqa.ingestion.tables import render_table

# [CLS] and [SEP] are added around every passage at embedding time.
SPECIAL_TOKENS = 2
MIN_BUDGET = 32

# A sub-heading is a short text block without sentence punctuation, e.g. "Net Sales by
# Category"; the table title is the nearest one within a few blocks above the table.
MAX_TITLE_CHARS = 80
TITLE_LOOKBACK = 4

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9“\"(\[])")


class Tokenizer(Protocol):
    def count_batch(self, texts: list[str]) -> list[int]: ...

    def split(self, text: str, max_tokens: int) -> list[str]:
        """Split text into consecutive pieces of at most `max_tokens` tokens."""
        ...

    def windows(self, text: str, size: int, overlap: int) -> list[tuple[int, int]]:
        """Character spans of consecutive `size`-token windows overlapping by `overlap`."""
        ...


ContextStyle = Literal["heading", "tables", "all"]


@dataclass(frozen=True)
class ChunkingConfig:
    strategy: Literal["section", "naive"] = "section"
    size: int = 512
    overlap: int = 64
    context: ContextStyle = "heading"

    def __post_init__(self) -> None:
        if not 0 <= self.overlap < self.size:
            raise ValueError("overlap must be >= 0 and smaller than size")
        if self.strategy == "naive" and self.context != "heading":
            raise ValueError("naive chunks have no sections or tables to put in a header")

    @property
    def key(self) -> str:
        """Identifier stored in `chunks.index_config`, e.g. "section-512-64" or
        "section-512-64-ctx-tables"."""
        base = f"{self.strategy}-{self.size}-{self.overlap}"
        return base if self.context == "heading" else f"{base}-ctx-{self.context}"


@dataclass
class ChunkDraft:
    section_index: int
    heading: str
    text: str
    token_count: int
    is_table: bool
    page_start: int | None
    page_end: int | None

    @property
    def embed_text(self) -> str:
        return f"{self.heading}\n{self.text}" if self.heading else self.text


@dataclass
class _Unit:
    text: str
    tokens: int
    page: int
    para_start: bool


def split_sentences(text: str) -> list[str]:
    return [s for s in _SENTENCE_SPLIT.split(text) if s.strip()]


def _reads_like_title(text: str) -> bool:
    """Starts like a heading or sentence: not a footnote "(a)", a "(In millions)" units line,
    a bullet, or a fragment continuing the previous sentence."""
    return bool(text) and text[0].isalnum() and not text[0].islower()


def _is_subheading(block: Block) -> bool:
    if not isinstance(block, TextBlock):
        return False
    text = block.text.strip()
    return (
        len(text) <= MAX_TITLE_CHARS
        and _reads_like_title(text)
        and not text.endswith((".", "!", "?", ",", ":", ";"))
    )


def table_title(blocks: list[Block], index: int, caption: str) -> str:
    """Short title for the table at `blocks[index]`: its nearest sub-heading, else its caption
    shortened to a few words."""
    for j in range(index - 1, max(-1, index - 1 - TITLE_LOOKBACK), -1):
        if _is_subheading(blocks[j]):
            return blocks[j].text.strip().rstrip(":").strip()
    caption = caption.strip()
    if not _reads_like_title(caption):
        return ""
    if len(caption) <= MAX_TITLE_CHARS:
        return caption.rstrip(":").strip()
    return caption[:MAX_TITLE_CHARS].rsplit(" ", 1)[0] + "\u2026"


def context_header(label: str, section: ParsedSection, title: str = "") -> str:
    """e.g. "Apple Inc. 10-K FY2026 | Item 7 MD&A | Net Sales by Category"."""
    if section.item_code:
        name = ITEM_SHORT_NAMES.get(section.item_code, "")
        where = f"Item {section.item_code} {name}".strip()
    else:
        where = section.title  # e.g. "Page 3" for PDFs
    return " | ".join(p for p in (label, where, title) if p)


def _join(units: list[_Unit]) -> str:
    out: list[str] = []
    for i, unit in enumerate(units):
        if i:
            out.append("\n\n" if unit.para_start else " ")
        out.append(unit.text)
    return "".join(out)


class SectionChunker:
    def __init__(self, tokenizer: Tokenizer, config: ChunkingConfig) -> None:
        self.tok = tokenizer
        self.config = config

    def chunk(self, doc: ParsedDocument, label: str) -> list[ChunkDraft]:
        drafts: list[ChunkDraft] = []
        for index, section in enumerate(doc.sections):
            drafts.extend(self._chunk_section(index, section, label))
        counts = self.tok.count_batch([d.text for d in drafts])
        for draft, count in zip(drafts, counts, strict=True):
            draft.token_count = count
        return drafts

    def _budget(self, heading: str) -> int:
        heading_tokens = self.tok.count_batch([heading])[0]
        return max(MIN_BUDGET, self.config.size - heading_tokens - SPECIAL_TOKENS)

    def _chunk_section(self, index: int, section: ParsedSection, label: str) -> list[ChunkDraft]:
        long_heading = f"{label} — {section.title}" if label else section.title
        context = self.config.context
        heading = context_header(label, section) if context == "all" else long_heading
        budget = self._budget(heading)
        drafts: list[ChunkDraft] = []
        pending: list[tuple[str, int, bool]] = []  # (sentence, page, starts paragraph)

        def flush_text() -> None:
            if pending:
                drafts.extend(self._pack_text(index, heading, pending, budget))
                pending.clear()

        for i, block in enumerate(section.blocks):
            if isinstance(block, TableBlock):
                rendered = render_table(block.rows, block.caption)
                if rendered.is_data:
                    flush_text()
                    table_heading, table_budget = heading, budget
                    if context != "heading":
                        title = table_title(section.blocks, i, block.caption)
                        table_heading = context_header(label, section, title)
                        table_budget = self._budget(table_heading)
                    drafts.extend(
                        self._pack_table(
                            index,
                            table_heading,
                            rendered.header,
                            rendered.rows,
                            block.page,
                            table_budget,
                        )
                    )
                    continue
                paragraphs = rendered.rows  # layout table: read it like text
            else:
                paragraphs = [block.text]
            for paragraph in paragraphs:
                for i, sentence in enumerate(split_sentences(paragraph)):
                    pending.append((sentence, block.page, i == 0))
        flush_text()
        return drafts

    def _pack_text(
        self, index: int, heading: str, sentences: list[tuple[str, int, bool]], budget: int
    ) -> list[ChunkDraft]:
        counts = self.tok.count_batch([s for s, _, _ in sentences])
        units: list[_Unit] = []
        for (text, page, para_start), count in zip(sentences, counts, strict=True):
            if count <= budget:
                units.append(_Unit(text, count, page, para_start))
                continue
            pieces = self.tok.split(text, budget)
            for j, (piece, n) in enumerate(zip(pieces, self.tok.count_batch(pieces), strict=True)):
                units.append(_Unit(piece, n, page, para_start and j == 0))

        drafts: list[ChunkDraft] = []
        current: list[_Unit] = []
        used = 0
        for unit in units:
            if current and used + unit.tokens > budget:
                drafts.append(self._text_draft(index, heading, current))
                carry: list[_Unit] = []
                carried = 0
                for prev in reversed(current):
                    if carried + prev.tokens > self.config.overlap:
                        break
                    carry.insert(0, prev)
                    carried += prev.tokens
                if carried + unit.tokens > budget:
                    carry, carried = [], 0
                current, used = carry, carried
            current.append(unit)
            used += unit.tokens
        if current:
            drafts.append(self._text_draft(index, heading, current))
        return drafts

    @staticmethod
    def _text_draft(index: int, heading: str, units: list[_Unit]) -> ChunkDraft:
        return ChunkDraft(
            section_index=index,
            heading=heading,
            text=_join(units),
            token_count=0,
            is_table=False,
            page_start=min(u.page for u in units),
            page_end=max(u.page for u in units),
        )

    def _pack_table(
        self,
        index: int,
        heading: str,
        header: list[str],
        rows: list[str],
        page: int,
        budget: int,
    ) -> list[ChunkDraft]:
        header_tokens = sum(self.tok.count_batch(header)) + len(header) if header else 0
        row_tokens = self.tok.count_batch(rows) if rows else []
        drafts: list[ChunkDraft] = []
        current: list[str] = []
        used = header_tokens
        for row, n in zip(rows, row_tokens, strict=True):
            # Rows are never split; an oversized row becomes its own chunk.
            if current and used + n + 1 > budget:
                drafts.append(self._table_draft(index, heading, header, current, page))
                current, used = [], header_tokens
            current.append(row)
            used += n + 1
        if current:
            drafts.append(self._table_draft(index, heading, header, current, page))
        return drafts

    @staticmethod
    def _table_draft(
        index: int, heading: str, header: list[str], rows: list[str], page: int
    ) -> ChunkDraft:
        return ChunkDraft(
            section_index=index,
            heading=heading,
            text="\n".join([*header, *rows]),
            token_count=0,
            is_table=True,
            page_start=page,
            page_end=page,
        )


class NaiveChunker:
    """Fixed token windows over the whole document's plain text, ignoring structure.

    Tables contribute their raw cell text (no row/column labels). Each chunk is attributed
    to the section and page where it starts, so it can still be cited.
    """

    def __init__(self, tokenizer: Tokenizer, config: ChunkingConfig) -> None:
        self.tok = tokenizer
        self.config = config

    def chunk(self, doc: ParsedDocument, label: str) -> list[ChunkDraft]:
        parts: list[str] = []
        spans: list[tuple[int, int, int]] = []  # (char start, section index, page)
        offset = 0
        for index, section in enumerate(doc.sections):
            for block in section.blocks:
                spans.append((offset, index, block.page))
                parts.append(block.text)
                offset += len(block.text) + 2
        text = "\n\n".join(parts)
        heading_tokens = self.tok.count_batch([label])[0] if label else 0
        size = max(MIN_BUDGET, self.config.size - heading_tokens - SPECIAL_TOKENS)
        overlap = min(self.config.overlap, size - 1)

        drafts: list[ChunkDraft] = []
        cursor = 0
        for start, end in self.tok.windows(text, size, overlap):
            while cursor + 1 < len(spans) and spans[cursor + 1][0] <= start:
                cursor += 1
            last = cursor
            while last + 1 < len(spans) and spans[last + 1][0] < end:
                last += 1
            drafts.append(
                ChunkDraft(
                    section_index=spans[cursor][1],
                    heading=label,
                    text=text[start:end],
                    token_count=0,
                    is_table=False,
                    page_start=spans[cursor][2],
                    page_end=spans[last][2],
                )
            )
        counts = self.tok.count_batch([d.text for d in drafts])
        for draft, count in zip(drafts, counts, strict=True):
            draft.token_count = count
        return drafts


def make_chunker(tokenizer: Tokenizer, config: ChunkingConfig) -> SectionChunker | NaiveChunker:
    if config.strategy == "naive":
        return NaiveChunker(tokenizer, config)
    return SectionChunker(tokenizer, config)
