"""PDF → per-page text and table blocks, using pdfplumber.

Each page becomes one section (pages are the citation unit for PDFs). Ruled tables found by
pdfplumber are rendered with the same labelled-row format as 10-K tables, and their
characters are excluded from the page text so numbers aren't indexed twice.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

import pdfplumber
from pdfminer.pdfdocument import PDFPasswordIncorrect
from pdfminer.pdfparser import PDFSyntaxError
from pdfminer.psexceptions import PSException
from pdfplumber.utils.exceptions import PdfminerException

from docqa.ingestion.html_blocks import Block, Cell, TableBlock, TextBlock, normalize_ws
from docqa.ingestion.parsed import DocumentParseError, ParsedDocument, ParsedSection

log = logging.getLogger(__name__)

_SENTENCE_END = re.compile(r"[.!?:;)\"”]$")


def _table_rows(raw: list[list[str | None]]) -> list[list[Cell]]:
    """pdfplumber marks merged cells as None; fold them into the previous cell's colspan."""
    rows: list[list[Cell]] = []
    for raw_row in raw:
        row: list[Cell] = []
        for value in raw_row:
            if value is None and row:
                row[-1].colspan += 1
            else:
                row.append(Cell(text=normalize_ws(value or "")))
        if any(c.text for c in row):
            rows.append(row)
    return rows


def _paragraphs(lines: list[dict[str, Any]]) -> list[tuple[float, str]]:
    """Group text lines into paragraphs: break after a short line that ends a sentence."""
    if not lines:
        return []
    widest = max(line["x1"] - line["x0"] for line in lines)
    paragraphs: list[tuple[float, str]] = []
    current: list[str] = []
    top = lines[0]["top"]
    prev_bottom: float | None = None
    for line in lines:
        text = line["text"].strip()
        if not text:
            continue
        height = line["bottom"] - line["top"]
        if current and prev_bottom is not None and line["top"] - prev_bottom > 0.8 * height:
            paragraphs.append((top, normalize_ws(" ".join(current))))  # blank-line gap
            current = []
        prev_bottom = line["bottom"]
        if not current:
            top = line["top"]
        if current and current[-1].endswith("-") and text[:1].islower():
            current[-1] = current[-1][:-1] + text  # re-join a hyphenated word
        else:
            current.append(text)
        short = (line["x1"] - line["x0"]) < 0.8 * widest
        if short and _SENTENCE_END.search(text):
            paragraphs.append((top, normalize_ws(" ".join(current))))
            current = []
    if current:
        paragraphs.append((top, normalize_ws(" ".join(current))))
    return paragraphs


def _page_blocks(page: Any, number: int) -> list[Block]:
    tables = page.find_tables()
    bboxes = [t.bbox for t in tables]

    def outside_tables(obj: dict[str, Any]) -> bool:
        if "x0" not in obj or "top" not in obj:
            return True
        cx = (obj["x0"] + obj["x1"]) / 2
        cy = (obj["top"] + obj["bottom"]) / 2
        return not any(x0 <= cx <= x1 and top <= cy <= bottom for x0, top, x1, bottom in bboxes)

    text_page = page.filter(outside_tables) if bboxes else page
    positioned: list[tuple[float, Block]] = [
        (top, TextBlock(text=text, page=number))
        for top, text in _paragraphs(text_page.extract_text_lines())
    ]
    for table in tables:
        rows = _table_rows(table.extract())
        if rows:
            positioned.append((table.bbox[1], TableBlock(rows=rows, page=number)))
    positioned.sort(key=lambda item: item[0])
    return [block for _, block in positioned]


def parse_pdf(path: Path) -> ParsedDocument:
    try:
        with pdfplumber.open(path) as pdf:
            sections = []
            for number, page in enumerate(pdf.pages, start=1):
                blocks = _page_blocks(page, number)
                for i, block in enumerate(blocks):
                    if isinstance(block, TableBlock) and i and isinstance(blocks[i - 1], TextBlock):
                        block.caption = blocks[i - 1].text[:250]
                sections.append(
                    ParsedSection(item_code=None, title=f"Page {number}", blocks=blocks)
                )
                page.close()  # release cached layout objects; keeps memory flat on long PDFs
            page_count = len(pdf.pages)
    except PdfminerException as exc:
        cause = exc.args[0] if exc.args else exc
        if isinstance(cause, PDFPasswordIncorrect):
            raise DocumentParseError("The PDF is password-protected.") from exc
        log.info("pdf parse failed for %s: %r", path, exc)
        raise DocumentParseError("The file could not be read as a PDF.") from exc
    except PDFPasswordIncorrect as exc:
        raise DocumentParseError("The PDF is password-protected.") from exc
    except (PDFSyntaxError, PSException, ValueError, KeyError, TypeError) as exc:
        log.info("pdf parse failed for %s: %r", path, exc)
        raise DocumentParseError("The file could not be read as a PDF.") from exc

    if not any(s.blocks for s in sections):
        raise DocumentParseError(
            "No extractable text found. Scanned (image-only) PDFs are not supported."
        )
    return ParsedDocument(sections=[s for s in sections if s.blocks], page_count=page_count)
