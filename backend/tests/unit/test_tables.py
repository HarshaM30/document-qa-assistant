from __future__ import annotations

from docqa.ingestion.html_blocks import Cell
from docqa.ingestion.tables import find_units, is_value, render_table


def row(*cells: str | tuple[str, int]) -> list[Cell]:
    return [Cell(c, 1) if isinstance(c, str) else Cell(c[0], c[1]) for c in cells]


def test_is_value() -> None:
    for v in ["1,234", "$1,234", "(4)", "(4)%", "12.5%", "—", "-", "2025", "N/A", "1.5x"]:
        assert is_value(v), v
    for v in ["Total", "Change", "(a)", "Year ended"]:
        assert not is_value(v), v


def test_currency_percent_and_paren_cells_merge() -> None:
    rendered = render_table(
        [
            row("", "2025", "", "2024"),
            row("Revenue", "$", "1,000", "", "$", "900"),
            row("Margin", "(4", ")%", "", "12", "%"),
        ]
    )
    assert rendered.rows == [
        "Revenue | 2025: $1,000 | 2024: $900",
        "Margin | 2025: (4)% | 2024: 12%",
    ]


def test_letter_footnotes_dropped_but_negative_numbers_kept() -> None:
    rendered = render_table(
        [row("", "2025", "2024"), row("Profit(a)", "(a)", "(7)", "5"), row("Loss", "(3)", "2")]
    )
    assert rendered.rows == ["Profit | 2025: (7) | 2024: 5", "Loss | 2025: (3) | 2024: 2"]


def test_misaligned_header_colspans() -> None:
    # Cell layout copied from a real filing whose header and data rows disagree on colspans.
    header = row(("", 3), ("2025", 3), ("", 3), ("2024", 3), ("", 3), ("Change", 3))
    revenue = row(
        ("Net revenue", 3), ("", 3), ("$", 1), ("182,447", 1), ("", 1),
        ("", 3), ("$", 1), ("177,556", 1), ("", 1), ("", 3), ("3", 2), ("%", 1),
    )  # fmt: skip
    ratio = row(("Return on equity", 3), ("", 3), ("17", 2), ("%", 1), ("", 3), ("18", 2), ("%", 1))
    rendered = render_table([header, revenue, ratio])
    assert rendered.rows[0] == "Net revenue | 2025: $182,447 | 2024: $177,556 | Change: 3%"
    # Two values, three columns, both nearest to "2024": fall back to left-aligned order.
    assert rendered.rows[1] == "Return on equity | 2025: 17% | 2024: 18%"


def test_layout_table_rendered_as_text() -> None:
    rendered = render_table([row("•", "We sell boots."), row("•", "We sell jackets.")])
    assert not rendered.is_data
    assert rendered.rows == ["• | We sell boots.", "• | We sell jackets."]


def test_find_units() -> None:
    assert find_units("Net sales (dollars in millions):") == "dollars in millions"
    assert find_units("(In thousands, except per share data)") == (
        "In thousands, except per share data"
    )
    assert find_units("No units here") == ""
