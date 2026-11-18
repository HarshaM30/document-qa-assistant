from __future__ import annotations

from typing import Any

import pytest

from docqa.evals.human_check import (
    agreement,
    cohens_kappa,
    export_markdown,
    parse_marks,
    select_records,
)


def _record(item_id: str, verdict: str) -> dict[str, Any]:
    return {
        "item_id": item_id,
        "question": f"Question {item_id}?",
        "answer": "Sales were $100 million [1].",
        "cited_chunk_ids": ["c1"],
        "passages": [{"chunk_id": "c1", "label": "Acme — Item 7", "text": "Sales | 2025: $100"}],
        "judge": {"verdict": verdict, "reason": "because", "unsupported_claims": []},
    }


def test_select_keeps_unfaithful_and_samples_the_rest() -> None:
    records = [_record(f"Q{i:02d}", "faithful") for i in range(30)]
    records += [
        _record("U1", "unfaithful"),
        _record("P1", "unparsed"),
        {"item_id": "R", "judge": None},
    ]
    picked = select_records(records, 20)
    ids = [r["item_id"] for r in picked]
    assert len(picked) == 20
    assert "U1" in ids
    assert "P1" not in ids
    assert "R" not in ids
    assert ids == sorted(ids)
    assert select_records(records, 20) == picked  # deterministic


def test_export_parse_round_trip() -> None:
    md = export_markdown([_record("A", "faithful"), _record("B", "unfaithful"),
                          _record("C", "faithful")], "qa_v1@x", "h")  # fmt: skip
    assert "- [ ] Agree with the judge" in md
    assert "★" in md
    assert [m.agree for m in parse_marks(md)] == [None, None, None]

    marked = md.replace("- [ ] Agree", "- [x] Agree", 1)  # A: agree
    second = marked.index("<!-- item: B")
    marked = marked[:second] + marked[second:].replace("- [ ] Disagree", "- [X] Disagree", 1)
    marks = parse_marks(marked)
    assert [(m.item_id, m.agree) for m in marks] == [("A", True), ("B", False), ("C", None)]
    assert marks[1].human_faithful is True  # judge said unfaithful, human disagreed

    result = agreement(marks)
    assert result.marked == 2
    assert result.agreed == 1
    assert result.rate == 0.5
    assert result.unmarked == ["C"]


def test_both_boxes_ticked_counts_as_unmarked() -> None:
    md = export_markdown([_record("A", "faithful")], "v", "h")
    both = md.replace("- [ ] Agree", "- [x] Agree").replace("- [ ] Disagree", "- [x] Disagree")
    assert parse_marks(both)[0].agree is None


def test_cohens_kappa() -> None:
    assert cohens_kappa([(True, True), (False, False)]) == 1.0
    assert cohens_kappa([(True, False), (False, True)]) == -1.0
    assert cohens_kappa([(True, True), (True, True)]) is None  # all one label: undefined
    assert cohens_kappa(
        [(True, True), (True, False), (False, False), (False, False)]
    ) == pytest.approx(0.5)
    assert cohens_kappa([]) is None
