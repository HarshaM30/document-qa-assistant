from __future__ import annotations

from typing import Any

from docqa.evals.dataset import NumericFact, QAItem
from docqa.evals.generation_eval import extract_numbers, score_record, states_number, summarize


def _fact(value: float, unit: str) -> NumericFact:
    return NumericFact(value=value, unit=unit, company="ACME", fiscal_year=2025)


def test_extract_numbers_skips_citation_markers() -> None:
    nums = extract_numbers("Sales were $416,161 million [1][2], or 76.2% [3, 4], up 15 percent.")
    assert (416161.0, 416161e6) in nums
    assert (76.2, 76.2) in nums
    assert all(raw not in (1, 2, 3, 4) for raw, _ in nums)


def test_states_number_accepts_scale_and_rounding() -> None:
    sales = _fact(416161, "USD millions")
    assert states_number("$416,161 million", sales)
    assert states_number("about $416.2 billion", sales)
    assert states_number("416,161 (in millions)", sales)
    assert not states_number("$391,035 million", sales)
    assert states_number("roughly 1.58 million employees", _fact(1576000, "employees"))
    assert states_number("14.6%", _fact(14.6, "percent"))
    assert states_number("$8.98 per share", _fact(8.98, "USD per share"))
    assert not states_number("$8.89 per share", _fact(8.98, "USD per share"))


def _item(answerable: bool = True, numeric: bool = True) -> QAItem:
    data: dict[str, Any] = {
        "id": "Q", "category": "table" if answerable else "unanswerable", "question": "q",
        "gold_answer": "a", "answerable": answerable, "companies": ["ACME"], "fiscal_years": [2025],
    }  # fmt: skip
    if answerable:
        data["sources"] = [{"doc": "ACME-FY2025", "section": "7", "quote": "long enough quote"}]
        if numeric:
            data["numeric"] = [
                {"value": 100, "unit": "USD millions", "company": "ACME", "fiscal_year": 2025}
            ]
    return QAItem.model_validate(data)


def _record(
    answer: str, refused: bool = False, cited: list[str] | None = None, **kw: Any
) -> dict[str, Any]:
    return {
        "answer": answer, "refused": refused, "gate_refused": False,
        "gold_chunk_ids": [["g1"]], "passages": [{"chunk_id": "g1"}, {"chunk_id": "x"}],
        "cited_chunk_ids": cited if cited is not None else ["g1"],
        "judge": {"verdict": "faithful", "reason": "", "unsupported_claims": []},
    } | kw  # fmt: skip


def test_score_record() -> None:
    good = score_record(_item(), _record("Sales were $100 million [1]."))
    assert good.numeric_correct
    assert good.citation_correct
    assert good.gold_retrieved
    assert good.faithful
    wrong_cite = score_record(_item(), _record("$100 million [2]", cited=["x"]))
    assert wrong_cite.numeric_correct
    assert wrong_cite.citation_correct is False
    refused = score_record(_item(), _record("I can't answer", refused=True, judge=None))
    assert refused.numeric_correct is False
    assert refused.citation_correct is None
    assert refused.faithful is None
    assert not refused.judged


def test_summarize_refusal_precision_recall() -> None:
    scores = [
        score_record(_item(False), _record("no", refused=True, judge=None)),  # TP
        score_record(_item(False), _record("made up", refused=False)),  # FN
        score_record(_item(), _record("no", refused=True, judge=None)),  # FP
        score_record(_item(), _record("$100 million [1]")),
    ]
    s = summarize(scores)
    assert s["refusals"] == {"true_positive": 1, "false_positive": 1, "false_negative": 1}
    assert s["refusal_precision"] == 0.5
    assert s["refusal_recall"] == 0.5
    assert s["numeric_accuracy"] == 0.5
    assert s["numeric_n"] == 2
    assert s["citation_accuracy"] == 1.0
    assert s["citation_n"] == 1


def test_line_referenced_citations_are_scored() -> None:
    score = score_record(_item(), _record("Sales were $100 million [1†L3-L4]."))
    assert score.citation_correct
    assert score.numeric_correct
