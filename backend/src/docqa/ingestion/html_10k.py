"""Split a 10-K HTML filing into Items (sections) of text and table blocks.

Heading detection
-----------------
Any short block that reads like "Item 7. Management's Discussion..." is a candidate. A filing
usually contains each heading more than once (table of contents, the real heading, sometimes
cross-references), so the parser keeps the chain of candidates that (a) follows the canonical
Item order and (b) covers the most text. Table-of-contents entries sit next to each other
with almost no text between them, so the real headings always win.

Running headers and footers ("Item 1A", "Apple Inc. | 2026 Form 10-K | 23", bare page
numbers) are removed before detection.

Incorporation by reference
--------------------------
Some filers (e.g. JPMorgan Chase) keep Items 7 and 8 as one-paragraph stubs that point to
"pages 46-160" of an annual-report section appended after Part IV. When an Item is such a
stub, the matching titled section ("Management's discussion and analysis", the auditor's
report / financial statements) is located in the trailing content and merged into the Item.
"""

from __future__ import annotations

import re
import string
from collections import Counter
from dataclasses import dataclass

from docqa.ingestion.html_blocks import Block, TableBlock, TextBlock, extract_blocks
from docqa.ingestion.parsed import DocumentParseError, ParsedDocument, ParsedSection

ITEM_ORDER = [
    "1", "1A", "1B", "1C", "2", "3", "4", "5", "6", "7", "7A", "8",
    "9", "9A", "9B", "9C", "10", "11", "12", "13", "14", "15", "16",
]  # fmt: skip
_RANK = {code: i for i, code in enumerate(ITEM_ORDER)}

_HEADING = re.compile(
    r"^(?:part\s+[iv]+\s*[,.\-\u2013\u2014:]?\s*)?item\s+(\d{1,2}[a-c]?)\s*[.:\-\u2013\u2014]*\s*"
    r"([A-Za-z\[“\"'(].{2,})$",
    re.I,
)
MAX_HEADING_CHARS = 250
_PART_DIVIDER = re.compile(r"^part\s+[iv]+\.?$")
MAX_BOILERPLATE_CHARS = 80
MAX_CAPTION_CHARS = 250

STUB_MAX_CHARS = 3000
_PAGE_REF = re.compile(r"\bpages?\s+\d", re.I)
_ALIASES = {
    "7": re.compile(r"^management.s discussion and analysis$", re.I),
    "8": re.compile(
        r"^(management.s report on internal control over financial reporting"
        r"|report of independent registered public accounting firm"
        r"|consolidated financial statements)$",
        re.I,
    ),
}
_TRAILING_MARKERS = re.compile(
    r"^(table of contents|three-year summary of consolidated financial highlights"
    r"|five-year stock performance|forward-looking statements|supplementary information"
    r"|glossary of terms)\b",
    re.I,
)


def _short_text(block: Block, limit: int) -> str | None:
    """Text of a block that could be a heading: a short paragraph or a 1-2 row table."""
    if isinstance(block, TableBlock) and len(block.rows) > 2:
        return None
    text = block.text
    return text if len(text) <= limit else None


def drop_boilerplate(blocks: list[Block], page_count: int) -> list[Block]:
    """Remove running headers/footers (short blocks repeated on many pages; the first is kept)
    and bare "PART II" dividers."""
    keys: list[str | None] = []
    for block in blocks:
        text = _short_text(block, MAX_BOILERPLATE_CHARS)
        keys.append(re.sub(r"\d+", "#", text.lower()) if text else None)
    counts = Counter(k for k in keys if k)
    threshold = max(4, page_count // 10)
    seen: set[str] = set()
    kept: list[Block] = []
    for block, key in zip(blocks, keys, strict=True):
        if key and _PART_DIVIDER.match(key):
            continue
        if key and counts[key] >= threshold:
            if key in seen or key == "#":
                continue
            seen.add(key)
        kept.append(block)
    return kept


@dataclass(frozen=True)
class _Candidate:
    index: int
    code: str
    title: str


def _candidates(blocks: list[Block]) -> list[_Candidate]:
    found = []
    for i, block in enumerate(blocks):
        text = _short_text(block, MAX_HEADING_CHARS)
        if not text:
            continue
        match = _HEADING.match(text)
        if match and match.group(1).upper() in _RANK:
            found.append(_Candidate(i, match.group(1).upper(), _clean_title(match.group(2))))
    return found


def _clean_title(title: str) -> str:
    title = title.strip().rstrip(".:").strip()
    return string.capwords(title) if title.isupper() else title


def select_headings(blocks: list[Block]) -> list[_Candidate]:
    """Weighted longest chain of candidates in canonical Item order (see module docstring)."""
    cands = _candidates(blocks)
    if not cands:
        return []
    sizes = [len(b.text) for b in blocks]
    weights = []
    for k, cand in enumerate(cands):
        end = cands[k + 1].index if k + 1 < len(cands) else len(blocks)
        weights.append(sum(sizes[cand.index + 1 : end]) + 1)

    best = weights[:]
    prev: list[int | None] = [None] * len(cands)
    for i in range(len(cands)):
        for j in range(i):
            if _RANK[cands[j].code] < _RANK[cands[i].code] and best[j] + weights[i] > best[i]:
                best[i] = best[j] + weights[i]
                prev[i] = j
    tail: int | None = max(range(len(cands)), key=best.__getitem__)
    chain = []
    while tail is not None:
        chain.append(cands[tail])
        tail = prev[tail]
    return chain[::-1]


def _attach_captions(section: ParsedSection) -> None:
    for i, block in enumerate(section.blocks):
        if isinstance(block, TableBlock) and i > 0:
            before = section.blocks[i - 1]
            if isinstance(before, TextBlock):
                block.caption = before.text[:MAX_CAPTION_CHARS]


def _relocate_stubs(sections: list[ParsedSection], trailing: list[Block]) -> list[ParsedSection]:
    """Merge incorporated-by-reference content from `trailing` into stub Items.

    Returns the extra (non-Item) sections found in the trailing content; whatever precedes
    the first anchor stays with the last Item.
    """
    stubs = {
        s.item_code: s
        for s in sections
        if s.item_code in _ALIASES
        and s.char_count < STUB_MAX_CHARS
        and _PAGE_REF.search(" ".join(b.text for b in s.blocks))
    }
    if not stubs:
        return []

    anchors: list[tuple[int, str | None, str]] = []  # (index, item code or None, title)
    used_aliases: set[str] = set()
    used_markers: set[str] = set()
    for i, block in enumerate(trailing):
        text = _short_text(block, MAX_BOILERPLATE_CHARS)
        if not text:
            continue
        for code, pattern in _ALIASES.items():
            if code in stubs and code not in used_aliases and pattern.match(text):
                anchors.append((i, code, text))
                used_aliases.add(code)
                break
        else:
            marker = _TRAILING_MARKERS.match(text)
            if marker and marker.group(1).lower() not in used_markers:
                used_markers.add(marker.group(1).lower())
                anchors.append((i, None, _clean_title(text)))
    if not used_aliases:
        return []

    sections[-1].blocks = sections[-1].blocks[: len(sections[-1].blocks) - len(trailing)]
    sections[-1].blocks.extend(trailing[: anchors[0][0]])
    extra: list[ParsedSection] = []
    for k, (start, anchor_code, title) in enumerate(anchors):
        end = anchors[k + 1][0] if k + 1 < len(anchors) else len(trailing)
        segment = trailing[start:end]
        if anchor_code is not None:
            stubs[anchor_code].blocks.extend(segment)
        else:
            extra.append(ParsedSection(item_code=None, title=title, blocks=segment))
    return extra


def parse_10k(source: bytes | str) -> ParsedDocument:
    blocks, page_count = extract_blocks(source)
    if not blocks:
        raise DocumentParseError("No text found in the filing.")
    blocks = drop_boilerplate(blocks, page_count)
    headings = select_headings(blocks)

    sections: list[ParsedSection] = []
    first = headings[0].index if headings else len(blocks)
    if first > 0:
        sections.append(ParsedSection(None, "Cover page and table of contents", blocks[:first]))
    for k, head in enumerate(headings):
        end = headings[k + 1].index if k + 1 < len(headings) else len(blocks)
        sections.append(
            ParsedSection(
                head.code, f"Item {head.code}. {head.title}", blocks[head.index + 1 : end]
            )
        )

    if headings:
        trailing = blocks[headings[-1].index + 1 :]
        sections.extend(_relocate_stubs(sections, trailing))

    for section in sections:
        _attach_captions(section)
    return ParsedDocument(sections=[s for s in sections if s.blocks], page_count=page_count)
