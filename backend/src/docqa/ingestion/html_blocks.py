"""Flatten (inline-XBRL) HTML into an ordered list of text and table blocks.

10-K documents are deeply nested `<div>`/`<span>` soup with inline XBRL tags mixed in. This
module streams the tree once and emits:
- `TextBlock` for each run of inline text between block-level boundaries, and
- `TableBlock` for each `<table>`, with cell text and colspans preserved.

It also tracks printed-page breaks (CSS `page-break-before/after`) so blocks carry an
approximate page number.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from lxml import etree, html

BLOCK_TAGS = frozenset(
    {
        "address", "article", "aside", "blockquote", "center", "dd", "div", "dl", "dt",
        "figcaption", "figure", "footer", "h1", "h2", "h3", "h4", "h5", "h6", "header",
        "hr", "li", "main", "nav", "ol", "p", "pre", "section", "ul", "body",
    }
)  # fmt: skip
SKIP_TAGS = frozenset({"script", "style", "head", "title", "noscript", "ix:header"})

_WS = re.compile(r"\s+")
_HIDDEN = re.compile(r"display\s*:\s*none", re.I)
_BREAK_BEFORE = re.compile(r"(?:page-)?break-before\s*:\s*(?:always|page)", re.I)
_BREAK_AFTER = re.compile(r"(?:page-)?break-after\s*:\s*(?:always|page)", re.I)
_ZERO_WIDTH = dict.fromkeys(map(ord, "​‌‍﻿"), None)


def normalize_ws(text: str) -> str:
    return _WS.sub(" ", text.replace("\xa0", " ").translate(_ZERO_WIDTH)).strip()


@dataclass
class TextBlock:
    text: str
    page: int


@dataclass
class Cell:
    text: str
    colspan: int = 1


@dataclass
class TableBlock:
    rows: list[list[Cell]]
    page: int
    caption: str = ""

    @property
    def text(self) -> str:
        """Plain text of the whole table (used for heading detection and debugging)."""
        return " ".join(c.text for row in self.rows for c in row if c.text)


Block = TextBlock | TableBlock


@dataclass
class _State:
    blocks: list[Block] = field(default_factory=list)
    buffer: list[str] = field(default_factory=list)
    page: int = 1

    def flush(self) -> None:
        if self.buffer:
            text = normalize_ws("".join(self.buffer))
            self.buffer.clear()
            if text:
                self.blocks.append(TextBlock(text=text, page=self.page))


def _tag(el: etree._Element) -> str:
    tag = el.tag
    return tag.lower() if isinstance(tag, str) else ""


def _is_hidden(el: etree._Element) -> bool:
    return bool(_HIDDEN.search(el.get("style", "")))


def _collect_text(node: etree._Element, parts: list[str]) -> None:
    if _tag(node) in SKIP_TAGS or _is_hidden(node):
        return
    if _tag(node) in {"br", "p", "div"}:
        parts.append(" ")
    if node.text:
        parts.append(node.text)
    for child in node:
        _collect_text(child, parts)
        if child.tail:
            parts.append(child.tail)


def _cell_text(cell: etree._Element) -> str:
    parts: list[str] = []
    _collect_text(cell, parts)
    return normalize_ws("".join(parts))


def _extract_table(table: etree._Element, page: int) -> TableBlock:
    rows: list[list[Cell]] = []
    for tr in table.iter("tr"):
        if _is_hidden(tr):
            continue
        cells = []
        for cell in tr:
            if _tag(cell) not in {"td", "th"}:
                continue
            try:
                colspan = max(1, int(cell.get("colspan", "1")))
            except ValueError:
                colspan = 1
            cells.append(Cell(text=_cell_text(cell), colspan=colspan))
        if any(c.text for c in cells):
            rows.append(cells)
    return TableBlock(rows=rows, page=page)


def extract_blocks(source: bytes | str) -> tuple[list[Block], int]:
    """Return (blocks in document order, number of printed pages)."""
    if isinstance(source, str):
        source = source.encode()
    parser = html.HTMLParser(encoding="utf-8", remove_comments=True, huge_tree=True)
    root = html.document_fromstring(source, parser=parser)
    state = _State()
    skip_until: etree._Element | None = None

    for event, el in etree.iterwalk(root, events=("start", "end")):
        if skip_until is not None:
            if event == "end" and el is skip_until:
                skip_until = None
                if el.tail:
                    state.buffer.append(el.tail)
            continue
        tag = _tag(el)
        if event == "start":
            style = el.get("style", "")
            if _BREAK_BEFORE.search(style):
                state.flush()
                state.page += 1
            if tag in SKIP_TAGS or _is_hidden(el):
                skip_until = el
                continue
            if tag == "table":
                state.flush()
                block = _extract_table(el, state.page)
                if block.rows:
                    state.blocks.append(block)
                skip_until = el
                continue
            if tag in BLOCK_TAGS:
                state.flush()
            elif tag == "br":
                state.buffer.append(" ")
            if el.text:
                state.buffer.append(el.text)
        else:
            if tag in BLOCK_TAGS:
                state.flush()
            if _BREAK_AFTER.search(el.get("style", "")):
                state.flush()
                state.page += 1
            if el.tail:
                state.buffer.append(el.tail)
    state.flush()
    # A trailing page break doesn't start a new page with content.
    last_page = max((b.page for b in state.blocks), default=1)
    return state.blocks, last_page
