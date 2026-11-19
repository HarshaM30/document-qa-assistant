"""Metadata filters from the question: which companies and fiscal years it asks about.

Library filings carry a ticker and fiscal year. A question that names a company and/or a
year ("What were Apple's iPhone net sales in fiscal 2026?") only needs that company's
filings for that year, so retrieval can skip the other 14. Uploaded documents carry no such
metadata and are never filtered out.

Year mapping. A 10-K for fiscal year Y also reports Y-1 (and Y-2 in the income statement),
so a year with no filing of its own (e.g. a comparative year) maps to the earliest later
filing that still reports it. A year no filing covers (e.g. 2015 or 2028) is ignored for
that company, so the question still reaches that company's filings and the refusal gate
decides.

Decomposition. A question about several companies or years becomes one sub-query per
(company, filing); `plan_subqueries` returns their document sets and the retriever merges
the results.
"""

from __future__ import annotations

import re
import uuid
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Literal

# Fiscal years covered by one 10-K: its own year and the two before it.
YEARS_REPORTED = 3

# Extra names for the library companies beyond their registered names.
EXTRA_ALIASES: dict[str, tuple[str, ...]] = {
    "AAPL": ("apple",),
    "MSFT": ("microsoft",),
    "AMZN": ("amazon", "aws", "amazon web services"),
    "JPM": ("jpmorgan", "jp morgan", "jpmorganchase", "jpmorgan chase", "chase"),
    "JNJ": ("johnson & johnson", "johnson and johnson", "j&j", "jnj"),
}
_LEGAL_SUFFIX = re.compile(
    r"[,.]?\s+(inc|incorporated|corp|corporation|co|company|& co|plc|ltd|llc)\.?$", re.I
)
_YEAR = re.compile(r"\b(?:fy\s?)?((?:19|20)\d{2})\b", re.I)
_SHORT_FY = re.compile(r"\bfy\s?(\d{2})\b", re.I)


@dataclass(frozen=True)
class FilingMeta:
    document_id: uuid.UUID
    ticker: str | None
    fiscal_year: int | None


@dataclass(frozen=True)
class QueryFilter:
    tickers: frozenset[str]
    years: frozenset[int]

    @property
    def empty(self) -> bool:
        return not (self.tickers or self.years)


def company_aliases(ticker: str, company_name: str | None) -> set[str]:
    names = {ticker.lower(), *EXTRA_ALIASES.get(ticker, ())}
    if company_name:
        name = company_name.lower().strip()
        names.add(name)
        stripped = _LEGAL_SUFFIX.sub("", name).strip()
        if stripped:
            names.add(stripped)
    return names


def _alias_pattern(alias: str) -> re.Pattern[str]:
    return re.compile(rf"(?<![\w&]){re.escape(alias)}(?![\w&])", re.I)


class CompanyMatcher:
    """Finds library companies mentioned in a question (word-boundary, case-insensitive)."""

    def __init__(self, companies: Iterable[tuple[str, str | None]]) -> None:
        self._patterns = [
            (ticker, _alias_pattern(alias))
            for ticker, name in companies
            for alias in sorted(company_aliases(ticker, name), key=len, reverse=True)
        ]

    def find(self, question: str) -> set[str]:
        return {ticker for ticker, pattern in self._patterns if pattern.search(question)}


def find_years(question: str) -> set[int]:
    years = {int(m.group(1)) for m in _YEAR.finditer(question)}
    years |= {2000 + int(m.group(1)) for m in _SHORT_FY.finditer(question)}
    return years


def detect(question: str, matcher: CompanyMatcher) -> QueryFilter:
    return QueryFilter(frozenset(matcher.find(question)), frozenset(find_years(question)))


def filings_for_year(year: int, available: Sequence[int]) -> int | None:
    """The filing that reports `year`: its own 10-K, else the earliest later one covering it."""
    if year in available:
        return year
    later = [fy for fy in available if year < fy < year + YEARS_REPORTED]
    return min(later) if later else None


@dataclass(frozen=True)
class SubQuery:
    """One retrieval: the documents it may search (None = no extra restriction)."""

    ticker: str | None
    fiscal_year: int | None
    document_ids: frozenset[uuid.UUID] | None


def plan_subqueries(
    flt: QueryFilter,
    filings: Sequence[FilingMeta],
    decompose: bool,
    by: Literal["filing", "company"] = "filing",
) -> list[SubQuery]:
    """Document sets to search for a question with filter `flt`.

    Without decomposition there is a single sub-query over every matching filing. With it,
    there is one per (company, filing year), e.g. Apple FY2025 + Microsoft FY2025 for a
    cross-company question, or with `by="company"` one per company over all of its matching
    filings. Untagged documents (uploads) are included in every sub-query.
    """
    if flt.empty:
        return [SubQuery(None, None, None)]
    untagged = frozenset(f.document_id for f in filings if not f.ticker)
    by_ticker: dict[str, list[FilingMeta]] = {}
    for f in filings:
        if f.ticker:
            by_ticker.setdefault(f.ticker, []).append(f)
    tickers = sorted(flt.tickers & by_ticker.keys()) if flt.tickers else sorted(by_ticker)
    if not tickers:  # names a company outside the library: nothing to narrow
        tickers = sorted(by_ticker) if flt.years else []
    if not tickers:
        return [SubQuery(None, None, None)]

    groups: list[SubQuery] = []
    for ticker in tickers:
        docs = by_ticker[ticker]
        available = sorted({d.fiscal_year for d in docs if d.fiscal_year is not None})
        wanted = sorted(
            {fy for y in flt.years if (fy := filings_for_year(y, available)) is not None}
        )
        if not wanted:  # no year given, or none this company filed: all its filings
            groups.append(SubQuery(ticker, None, frozenset(d.document_id for d in docs)))
            continue
        for fy in wanted:
            ids = frozenset(d.document_id for d in docs if d.fiscal_year == fy)
            groups.append(SubQuery(ticker, fy, ids))

    if by == "company":
        per_company: dict[str | None, frozenset[uuid.UUID]] = {}
        for g in groups:
            per_company[g.ticker] = per_company.get(g.ticker, frozenset()) | (
                g.document_ids or frozenset()
            )
        groups = [SubQuery(t, None, ids) for t, ids in per_company.items()]

    if decompose and len(groups) > 1:
        return [
            SubQuery(g.ticker, g.fiscal_year, (g.document_ids or frozenset()) | untagged)
            for g in groups
        ]
    merged = frozenset().union(*(g.document_ids or frozenset() for g in groups)) | untagged
    return [SubQuery(None, None, merged)]


def interleave[K](rankings: Sequence[Sequence[K]], limit: int) -> list[K]:
    """Round-robin merge of ranked lists (first of each, then second of each, ...), deduped."""
    out: list[K] = []
    seen: set[K] = set()
    depth = max((len(r) for r in rankings), default=0)
    for i in range(depth):
        for ranking in rankings:
            if i < len(ranking) and ranking[i] not in seen:
                seen.add(ranking[i])
                out.append(ranking[i])
                if len(out) == limit:
                    return out
    return out
