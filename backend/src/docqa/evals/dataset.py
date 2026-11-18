"""Eval dataset: schema, loader, source-quote verification, and gold chunks.

Every answerable question carries one or more sources (filing, Item, exact quote). The quote
must appear in the parsed filing text, rendered the same way the chunker renders it (tables
as `Row | Column: value` lines), so it can be traced to the chunks that contain it.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field, model_validator

from docqa.config import REPO_ROOT
from docqa.ingestion.edgar import Lockfile
from docqa.ingestion.html_10k import parse_10k
from docqa.ingestion.html_blocks import TableBlock
from docqa.ingestion.parsed import ParsedDocument
from docqa.ingestion.tables import render_table

DATASET_DIR = REPO_ROOT / "evals" / "datasets"
DEFAULT_DATASET = DATASET_DIR / "qa_v1.jsonl"

_DOC_ID = re.compile(r"^(?P<ticker>[A-Z]+)-FY(?P<year>\d{4})$")


class Category(StrEnum):
    FACTUAL = "factual"
    TABLE = "table"
    YOY = "yoy"
    CROSS_COMPANY = "cross_company"
    UNANSWERABLE = "unanswerable"


class Source(BaseModel):
    doc: str = Field(pattern=_DOC_ID.pattern, description='Filing id, e.g. "AAPL-FY2026"')
    section: str = Field(description='10-K Item code, e.g. "7" or "1A"')
    quote: str = Field(min_length=10)

    @property
    def ticker(self) -> str:
        m = _DOC_ID.match(self.doc)
        assert m
        return m["ticker"]

    @property
    def fiscal_year(self) -> int:
        m = _DOC_ID.match(self.doc)
        assert m
        return int(m["year"])


class NumericFact(BaseModel):
    """A number the answer must state, e.g. 416161 "USD millions"."""

    value: float
    unit: str
    company: str
    fiscal_year: int
    xbrl_concept: str | None = Field(
        default=None, description='e.g. "us-gaap:Revenues"; None if XBRL has no such fact'
    )
    xbrl_note: str | None = Field(
        default=None, description="Why this value is not (or differently) tagged in XBRL"
    )


class QAItem(BaseModel):
    id: str
    category: Category
    question: str
    gold_answer: str
    answerable: bool
    companies: list[str]
    fiscal_years: list[int]
    sources: list[Source] = Field(default_factory=list)
    numeric: list[NumericFact] = Field(default_factory=list)

    @model_validator(mode="after")
    def _consistent(self) -> QAItem:
        if self.answerable == (self.category == Category.UNANSWERABLE):
            raise ValueError(f"{self.id}: answerable must be false exactly for unanswerables")
        if self.answerable and not self.sources:
            raise ValueError(f"{self.id}: answerable questions need at least one source")
        if not self.answerable and (self.sources or self.numeric):
            raise ValueError(f"{self.id}: unanswerable questions carry no sources or numbers")
        return self


@dataclass(frozen=True)
class Dataset:
    path: Path
    items: list[QAItem]

    @property
    def name(self) -> str:
        return self.path.stem

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.path.read_bytes()).hexdigest()

    @property
    def version(self) -> str:
        """Recorded in every report: file name plus a content hash, e.g. "qa_v1@3f2a9c1b"."""
        return f"{self.name}@{self.sha256[:8]}"

    @property
    def answerable(self) -> list[QAItem]:
        return [i for i in self.items if i.answerable]


def load_dataset(path: Path = DEFAULT_DATASET) -> Dataset:
    items = [
        QAItem.model_validate_json(line)
        for line in path.read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("//")
    ]
    ids = [i.id for i in items]
    duplicates = {i for i in ids if ids.count(i) > 1}
    if duplicates:
        raise ValueError(f"duplicate question ids: {sorted(duplicates)}")
    return Dataset(path, items)


# --- Text normalization and matching ---------------------------------------------------

_PUNCT = str.maketrans(
    {0x2018: "'", 0x2019: "'", 0x201C: '"', 0x201D: '"', 0x2013: "-", 0x2014: "-"}
)
_WS = re.compile(r"\s+")
_TOKEN = re.compile(r"[a-z0-9]+(?:[.,][0-9]+)*")


def normalize(text: str) -> str:
    """Case, whitespace, and quote/dash style don't matter when matching quotes."""
    return _WS.sub(" ", text.translate(_PUNCT).replace("\xa0", " ")).strip().lower()


def tokens(text: str) -> set[str]:
    """Word and number tokens; thousands separators dropped so "1,234" == "1234"."""
    return {t.replace(",", "") for t in _TOKEN.findall(normalize(text))}


def contains_quote(text: str, quote: str) -> bool:
    return normalize(quote) in normalize(text)


def contains_quote_tokens(text: str, quote: str) -> bool:
    """Every token of the quote appears in the text (order ignored).

    The fallback for chunkers that don't render tables as labelled rows: a naive chunk holds
    the row label and the value, but not the `Row | Column: value` layout.
    """
    return tokens(quote) <= tokens(text)


def gold_chunk_ids[K](quote: str, chunks: Iterable[tuple[K, str]]) -> list[K]:
    """Chunks of the source filing that contain the quote.

    Exact (normalized) containment wins; if no chunk contains the quote verbatim, chunks that
    contain every token of it count instead.
    """
    chunks = list(chunks)
    exact = [cid for cid, text in chunks if contains_quote(text, quote)]
    if exact:
        return exact
    return [cid for cid, text in chunks if contains_quote_tokens(text, quote)]


# --- Parsed filing text ------------------------------------------------------------------


def section_texts(parsed: ParsedDocument) -> list[tuple[str | None, str, str]]:
    """(item code, title, text) per section, with tables rendered as the chunker renders them."""
    out = []
    for section in parsed.sections:
        parts: list[str] = []
        for block in section.blocks:
            if isinstance(block, TableBlock):
                rendered = render_table(block.rows, block.caption)
                parts.append(rendered.text if rendered.is_data else "\n".join(rendered.rows))
            else:
                parts.append(block.text)
        out.append((section.item_code, section.title, "\n".join(parts)))
    return out


@dataclass(frozen=True)
class QuoteCheck:
    item_id: str
    source: Source
    found_in_section: bool
    found_elsewhere: list[str]  # item codes / titles where it was found instead

    @property
    def ok(self) -> bool:
        return self.found_in_section


def verify_quotes(
    items: Sequence[QAItem], filings: Mapping[str, Sequence[tuple[str | None, str, str]]]
) -> list[QuoteCheck]:
    """Check every source quote against its filing's parsed text (keyed by doc id)."""
    checks = []
    for item in items:
        for source in item.sources:
            sections = filings.get(source.doc)
            if sections is None:
                checks.append(QuoteCheck(item.id, source, False, ["<filing not found>"]))
                continue
            hits = [
                (code, title)
                for code, title, text in sections
                if contains_quote(text, source.quote)
            ]
            in_section = any(code == source.section for code, _ in hits)
            elsewhere = [code or title for code, title in hits if code != source.section]
            checks.append(QuoteCheck(item.id, source, in_section, elsewhere))
    return checks


def doc_id(ticker: str, fiscal_year: int) -> str:
    return f"{ticker}-FY{fiscal_year}"


def load_filing_texts(
    raw_dir: Path, lock: Lockfile, doc_ids: Iterable[str] | None = None
) -> dict[str, list[tuple[str | None, str, str]]]:
    """Parse the locked filings (optionally only `doc_ids`) into per-section text."""
    wanted = set(doc_ids) if doc_ids is not None else None
    out = {}
    for entry in lock.filings:
        key = doc_id(entry.ticker, entry.fiscal_year)
        path = raw_dir / entry.local_path
        if (wanted is not None and key not in wanted) or not path.exists():
            continue
        out[key] = section_texts(parse_10k(path.read_bytes()))
    return out
