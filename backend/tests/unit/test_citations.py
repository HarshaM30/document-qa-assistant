from __future__ import annotations

from docqa.generation.citations import normalize_markers, parse_markers, resolve_citations
from tests.unit.fakes import make_passage

PASSAGES = [make_passage(n) for n in (1, 2, 3)]


def test_single_marker() -> None:
    assert parse_markers("Revenue was $10 million [1].") == [1]


def test_adjacent_markers() -> None:
    assert parse_markers("Both segments grew [1][3].") == [1, 3]


def test_comma_separated_markers() -> None:
    assert parse_markers("Both grew [1, 3] and [2,3].") == [1, 3, 2]


def test_order_of_first_appearance_without_duplicates() -> None:
    assert parse_markers("A [2]. B [1]. C [2][1].") == [2, 1]


def test_lenticular_and_fullwidth_brackets() -> None:
    text = "Sales rose \N{LEFT BLACK LENTICULAR BRACKET}3\N{RIGHT BLACK LENTICULAR BRACKET}"
    text += " and fell \N{FULLWIDTH LEFT SQUARE BRACKET}1\N{FULLWIDTH RIGHT SQUARE BRACKET}."
    assert parse_markers(text) == [3, 1]
    assert normalize_markers(text) == "Sales rose [3] and fell [1]."


def test_non_numeric_brackets_ignored() -> None:
    assert parse_markers("See [a], [1a], [], [ 2 ] and [note].") == [2]


def test_resolve_maps_markers_to_passages() -> None:
    [first, third] = resolve_citations("Up [3]. Down [1].", PASSAGES)
    assert (first.marker, first.chunk_id) == (3, PASSAGES[2].chunk_id)
    assert (third.marker, third.chunk_id) == (1, PASSAGES[0].chunk_id)
    assert first.section_title == "Item 3"
    assert first.page_start == 3


def test_resolve_drops_markers_without_a_passage() -> None:
    cited = resolve_citations("A [0]. B [2]. C [4]. D [99].", PASSAGES)
    assert [c.marker for c in cited] == [2]
    assert resolve_citations("No sources [1].", []) == []


def test_line_referenced_markers_count_as_their_passage() -> None:
    assert parse_markers("EPS was $8.98 [1\u2020L9-L10][6\u2020L7-L8].") == [1, 6]
    assert parse_markers("See [2, 3\u2020L1]") == [2, 3]
