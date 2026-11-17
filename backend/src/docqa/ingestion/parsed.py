"""Parser output shared by the 10-K HTML and PDF parsers."""

from __future__ import annotations

from dataclasses import dataclass, field

from docqa.ingestion.html_blocks import Block


class DocumentParseError(Exception):
    """A parse failure with a message safe to show to the user."""


@dataclass
class ParsedSection:
    """A citation unit: a 10-K Item, or one page of a PDF."""

    item_code: str | None
    title: str
    blocks: list[Block] = field(default_factory=list)

    @property
    def page_start(self) -> int | None:
        return self.blocks[0].page if self.blocks else None

    @property
    def page_end(self) -> int | None:
        return self.blocks[-1].page if self.blocks else None

    @property
    def char_count(self) -> int:
        return sum(len(b.text) for b in self.blocks)


@dataclass
class ParsedDocument:
    sections: list[ParsedSection]
    page_count: int

    def item(self, code: str) -> ParsedSection | None:
        return next((s for s in self.sections if s.item_code == code), None)

    @property
    def item_codes(self) -> list[str]:
        return [s.item_code for s in self.sections if s.item_code]
