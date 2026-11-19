from __future__ import annotations

import uuid

import pytest

from docqa.retrieval.query_filters import (
    CompanyMatcher,
    FilingMeta,
    QueryFilter,
    SubQuery,
    detect,
    filings_for_year,
    find_years,
    interleave,
    plan_subqueries,
)
from docqa.retrieval.retriever import RetrievalConfig

COMPANIES = [
    ("AAPL", "Apple Inc."),
    ("MSFT", "MICROSOFT CORP"),
    ("AMZN", "AMAZON COM INC"),
    ("JPM", "JPMORGAN CHASE & CO"),
    ("JNJ", "JOHNSON & JOHNSON"),
]
MATCHER = CompanyMatcher(COMPANIES)


def _filings() -> list[FilingMeta]:
    years = {
        "AAPL": (2024, 2025, 2026),
        "MSFT": (2024, 2025, 2026),
        "AMZN": (2023, 2024, 2025),
    }
    out = [
        FilingMeta(uuid.uuid5(uuid.NAMESPACE_URL, f"{t}{y}"), t, y)
        for t, ys in years.items()
        for y in ys
    ]
    out.append(FilingMeta(uuid.UUID(int=1), None, None))  # an uploaded PDF
    return out


def _id(ticker: str, year: int) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_URL, f"{ticker}{year}")


UPLOAD = uuid.UUID(int=1)


@pytest.mark.parametrize(
    ("question", "tickers"),
    [
        ("What were Apple's iPhone net sales?", {"AAPL"}),
        ("How did AWS net sales change?", {"AMZN"}),
        ("Compare Amazon's and Microsoft's net income.", {"AMZN", "MSFT"}),
        ("How many employees did JPMorgan Chase have?", {"JPM"}),
        ("What was J&J's R&D expense?", {"JNJ"}),
        ("Johnson & Johnson total assets", {"JNJ"}),
        ("What did the company purchase?", set()),  # "chase" only as a whole word
        ("What was Tesla's revenue?", set()),
        ("pineapple exports", set()),
    ],
)
def test_detects_companies(question: str, tickers: set[str]) -> None:
    assert MATCHER.find(question) == tickers


def test_detects_years() -> None:
    assert find_years("from fiscal 2025 to fiscal 2026") == {2025, 2026}
    assert find_years("FY2024 and FY23") == {2024, 2023}
    assert find_years("about 2,000 people and $1,999 million") == set()


def test_year_maps_to_its_filing_or_the_earliest_later_one() -> None:
    assert filings_for_year(2025, [2024, 2025, 2026]) == 2025
    assert filings_for_year(2023, [2024, 2025, 2026]) == 2024  # comparative year
    assert filings_for_year(2022, [2024, 2025, 2026]) == 2024  # 10-K reports 2022-2024
    assert filings_for_year(2021, [2024, 2025, 2026]) is None
    assert filings_for_year(2022, [2023, 2024, 2025]) == 2023
    assert filings_for_year(2028, [2024, 2025, 2026]) is None


def test_no_metadata_means_no_restriction() -> None:
    flt = detect("What are the main risk factors?", MATCHER)
    assert flt.empty
    assert plan_subqueries(flt, _filings(), decompose=True) == [SubQuery(None, None, None)]


def test_company_and_year_narrow_to_one_filing_plus_uploads() -> None:
    flt = detect("What were Apple's net sales in fiscal 2025?", MATCHER)
    [sub] = plan_subqueries(flt, _filings(), decompose=True)
    assert sub.document_ids == frozenset({_id("AAPL", 2025), UPLOAD})


def test_company_without_year_keeps_all_its_filings() -> None:
    [sub] = plan_subqueries(QueryFilter(frozenset({"AMZN"}), frozenset()), _filings(), False)
    assert sub.document_ids == frozenset({_id("AMZN", y) for y in (2023, 2024, 2025)}) | {UPLOAD}


def test_year_no_filing_covers_is_ignored() -> None:
    flt = detect("What were Apple's net sales in fiscal 2015?", MATCHER)
    [sub] = plan_subqueries(flt, _filings(), decompose=False)
    assert sub.document_ids == frozenset({_id("AAPL", y) for y in (2024, 2025, 2026)}) | {UPLOAD}


def test_year_without_company_filters_every_company() -> None:
    flt = detect("Which company had the highest revenue in 2023?", MATCHER)
    [sub] = plan_subqueries(flt, _filings(), decompose=False)
    # 2023 is reported in Apple's and Microsoft's FY2024 10-Ks and Amazon's FY2023 10-K.
    assert sub.document_ids == frozenset(
        {
            _id("AAPL", 2024),
            _id("MSFT", 2024),
            _id("AMZN", 2023),
            UPLOAD,
        }
    )


def test_unknown_company_without_year_is_not_filtered() -> None:
    flt = detect("What was Tesla's revenue?", MATCHER)
    assert plan_subqueries(flt, _filings(), decompose=True) == [SubQuery(None, None, None)]


def test_decomposes_cross_company_and_multi_year_questions() -> None:
    flt = detect("Compare Amazon's and Microsoft's net income for fiscal 2025.", MATCHER)
    subs = plan_subqueries(flt, _filings(), decompose=True)
    assert [(s.ticker, s.fiscal_year) for s in subs] == [("AMZN", 2025), ("MSFT", 2025)]
    assert subs[0].document_ids == frozenset({_id("AMZN", 2025), UPLOAD})

    flt = detect("How did Apple's net sales change from fiscal 2025 to fiscal 2026?", MATCHER)
    subs = plan_subqueries(flt, _filings(), decompose=True)
    assert [(s.ticker, s.fiscal_year) for s in subs] == [("AAPL", 2025), ("AAPL", 2026)]

    # Without decomposition the same filings are searched together.
    [merged] = plan_subqueries(flt, _filings(), decompose=False)
    assert merged.document_ids == frozenset({_id("AAPL", 2025), _id("AAPL", 2026), UPLOAD})


def test_years_mapping_to_the_same_filing_are_one_subquery() -> None:
    # Apple's FY2024 10-K reports both 2023 and 2024.
    flt = detect("How did Apple's Services net sales change from 2023 to 2024?", MATCHER)
    subs = plan_subqueries(flt, _filings(), decompose=True)
    assert len(subs) == 1
    assert subs[0].document_ids == frozenset({_id("AAPL", 2024), UPLOAD})


def test_interleave_round_robin_and_dedupe() -> None:
    assert interleave([["a1", "a2", "a3"], ["b1", "a1", "b3"]], 10) == [
        "a1",
        "b1",
        "a2",
        "a3",
        "b3",
    ]
    assert interleave([["a1", "a2"], ["b1", "b2"]], 3) == ["a1", "b1", "a2"]
    assert interleave([], 5) == []


def test_decompose_requires_metadata_filter() -> None:
    with pytest.raises(ValueError, match="metadata_filter"):
        RetrievalConfig("section-512-64", decompose=True)


def test_decompose_by_company_keeps_each_companys_years_together() -> None:
    flt = detect("How did Apple's net sales change from fiscal 2025 to fiscal 2026?", MATCHER)
    [sub] = plan_subqueries(flt, _filings(), decompose=True, by="company")
    assert sub.document_ids == frozenset({_id("AAPL", 2025), _id("AAPL", 2026), UPLOAD})

    flt = detect("Compare Amazon and Microsoft revenue in 2024 and 2025.", MATCHER)
    subs = plan_subqueries(flt, _filings(), decompose=True, by="company")
    assert [s.ticker for s in subs] == ["AMZN", "MSFT"]
    assert subs[1].document_ids == frozenset({_id("MSFT", 2024), _id("MSFT", 2025), UPLOAD})
