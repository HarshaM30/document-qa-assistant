"""Render tables as labelled text so every number stays attached to its meaning.

A financial table such as

    |                | 2026      | Change | 2025      |
    | Americas       | $ 198,083 | 11 %   | $ 178,353 |

becomes

    Americas | 2026: $198,083 | Change: 11% | 2025: $178,353

Filings split currency symbols, closing parentheses and percent signs into their own cells
and pad with empty spacer cells; those are merged back into the value they belong to.
Values are matched to column headers by order when the counts agree, and otherwise by
column position (nearest header centre), which tolerates filers whose header rows and data
rows use different colspans.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from docqa.ingestion.html_blocks import Cell

_CURRENCY = {"$", "€", "£", "¥", "US$"}
_SUFFIXES = re.compile(r"^(\)|%|\)%|%\)|pts?|bps|x)$", re.I)
_FOOTNOTE = re.compile(r"^(\([a-z]{1,2}\)|\*+|†|‡)$")  # "(4)" is a negative number, "(a)" a note
_NUMERIC = re.compile(
    r"^[\$€£¥]?\s*\(?\s*[-\u2013\u2014+]?\s*[\$€£¥]?\s*\d[\d,]*(\.\d+)?\s*\)?\s*(%|x|pts?|bps)?\)?$",
    re.I,
)
_DASH = re.compile(r"^[-\u2013\u2014]+$")
_UNITS = re.compile(
    r"\(?\s*((?:dollars|amounts|\$)?\s*in\s+(?:millions|thousands|billions)"
    r"(?:\s+of\s+[a-z. ]+)?(?:,?\s*except[^)]*)?)\s*\)?",
    re.I,
)


def is_value(text: str) -> bool:
    t = text.replace(" ", "")
    return bool(_NUMERIC.match(text) or _DASH.match(t) or t.upper() in {"N/A", "NM", "N/M"})


def find_units(*texts: str) -> str:
    for text in texts:
        match = _UNITS.search(text)
        if match:
            return match.group(1).strip().rstrip(",")
    return ""


@dataclass
class _Span:
    text: str
    start: int
    end: int  # exclusive

    @property
    def center(self) -> float:
        return (self.start + self.end - 1) / 2


def _positioned(row: list[Cell]) -> list[_Span]:
    spans, col = [], 0
    for cell in row:
        spans.append(_Span(cell.text, col, col + cell.colspan))
        col += cell.colspan
    return spans


def _merge_row(row: list[Cell]) -> list[_Span]:
    """Drop spacer cells and glue `$`, `)` and `%` fragments onto their values."""
    merged: list[_Span] = []
    pending_prefix: _Span | None = None
    for span in _positioned(row):
        text = span.text.strip()
        if not text or _FOOTNOTE.match(text):
            continue
        if text in _CURRENCY:
            pending_prefix = span
            continue
        if _SUFFIXES.match(text) and merged:
            prev = merged[-1]
            merged[-1] = _Span(prev.text + text, prev.start, span.end)
            continue
        if pending_prefix is not None:
            span = _Span(pending_prefix.text + text, pending_prefix.start, span.end)
            pending_prefix = None
        else:
            span = _Span(text, span.start, span.end)
        merged.append(span)
    return merged


def _clean_label(text: str) -> str:
    # Trailing footnote markers on labels, e.g. "Pre-provision profit(a)".
    return re.sub(r"(\([a-z]\))+$", "", text).rstrip(" :").strip()


@dataclass
class RenderedTable:
    header: list[str]  # caption / units lines, repeated on every chunk of a split table
    rows: list[str]
    is_data: bool

    @property
    def text(self) -> str:
        return "\n".join([*self.header, *self.rows])


def _label_columns(leaf: list[_Span], parents: list[list[_Span]]) -> list[str]:
    labels = []
    for span in leaf:
        parts = []
        for parent_row in parents:
            for parent in parent_row:
                if parent.start <= span.center < parent.end and parent.text != span.text:
                    parts.append(parent.text)
                    break
        parts.append(span.text)
        labels.append(" ".join(parts))
    return labels


def _assign(values: list[_Span], headers: list[_Span], labels: list[str]) -> list[str]:
    if not headers:
        return [""] * len(values)
    if len(values) == len(headers):
        return labels
    picks = [
        min(range(len(headers)), key=lambda i: abs(headers[i].center - value.center))
        for value in values
    ]
    if len(set(picks)) < len(picks) and len(values) < len(headers):
        # Two values claimed the same column: header and data colspans disagree. Values are
        # almost always left-aligned under the leading columns, so fall back to order.
        return labels[: len(values)]
    return [labels[i] for i in picks]


def render_table(rows: list[list[Cell]], caption: str = "") -> RenderedTable:
    merged_rows = [_merge_row(r) for r in rows]
    merged_rows = [r for r in merged_rows if r]
    value_rows = sum(1 for r in merged_rows if sum(is_value(s.text) for s in r[1:]) >= 1)

    if value_rows < 2:
        # Layout or text table (bullets, headings, exhibit lists): keep the reading order.
        lines = [" | ".join(s.text for s in r) for r in merged_rows]
        return RenderedTable(header=[], rows=[ln for ln in lines if ln], is_data=False)

    # Units live in the caption or in the label column / a full-width row above the data,
    # never in a column header such as "Square Feet (in thousands)".
    unit_sources = [caption]

    out: list[str] = []
    header_stack: list[list[_Span]] = []
    leaf: list[_Span] = []
    labels: list[str] = []
    group = ""
    seen_data = False
    for row in merged_rows:
        has_label = row[0].start == 0 and not is_value(row[0].text)
        cells = row[1:] if has_label else row
        values_here = [s for s in cells if is_value(s.text)]
        if not seen_data and (has_label or len(row) == 1):
            unit_sources.append(row[0].text)
        if (
            not has_label
            and cells
            and (not seen_data or not values_here or _looks_like_header(cells))
        ):
            # Column header row (possibly repeated mid-table).
            if len(cells) == 1 and len(cells[0].text) > 60 and not seen_data:
                continue  # a long caption-like line inside the table, e.g. "(in millions ...)"
            if seen_data:
                header_stack = []
            header_stack.append(cells)
            leaf = header_stack[-1]
            labels = _label_columns(leaf, header_stack[:-1])
            continue
        if has_label and not cells:
            group = _clean_label(row[0].text)  # sub-heading like "Net sales:"
            continue
        if has_label and not seen_data and _looks_like_header(cells):
            # Header row whose first cell is a title, e.g. "Year ended | 2026 | 2025".
            header_stack.append(cells)
            leaf = header_stack[-1]
            labels = _label_columns(leaf, header_stack[:-1])
            continue
        seen_data = True
        label = _clean_label(row[0].text) if has_label else ""
        if group and label and label != group:
            label = f"{group} > {label}"
        names = _assign(cells, leaf, labels)
        parts = [f"{n}: {c.text}" if n else c.text for n, c in zip(names, cells, strict=True)]
        out.append(" | ".join([label or "(row)", *parts]))
        if label.split(" > ")[-1].lower().startswith("total"):
            group = ""  # a "Total ..." row closes its group

    header_lines = [f"Table: {caption}"] if caption else []
    units = find_units(*unit_sources)
    if units:
        header_lines.append(f"Units: {units}")
    return RenderedTable(header=header_lines, rows=out, is_data=True)


_YEARish = re.compile(r"^(fy\s*)?(19|20)\d{2}$", re.I)


def _looks_like_header(cells: list[_Span]) -> bool:
    return all(_YEARish.match(c.text.strip()) or not is_value(c.text) for c in cells)
