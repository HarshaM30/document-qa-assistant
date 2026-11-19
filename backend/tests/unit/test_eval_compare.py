from __future__ import annotations

from typing import Any

import pytest

from docqa.evals.compare import render_comparison


def _retrieval(recall10: float, mrr: float, **config: Any) -> dict[str, Any]:
    return {
        "dataset": "qa_v1@abc",
        "created_at": "20261119T000000Z",
        "config": {"index_config": "section-512-64", **config},
        "overall": {"n": 2, "recall": {"5": recall10 / 2, "10": recall10}, "mrr": mrr},
        "by_category": {"table": {"n": 2, "recall": {"5": 0.0, "10": recall10}, "mrr": mrr}},
        "mean_seconds": 1.0,
    }


def _generation(numeric: list[bool], refused: list[bool]) -> dict[str, Any]:
    return {
        "dataset": "qa_v1@abc",
        "run_hash": "r",
        "answer_model": "a",
        "judge_model": "j",
        "summary": {
            "questions": 2,
            "numeric_accuracy": sum(numeric) / 2,
            "numeric_n": 3,
            "refusal_precision": 0.5,
            "refusal_recall": 1.0,
            "refusals": {"true_positive": 1, "false_positive": 1, "false_negative": 0},
        },
        "items": [
            {"item_id": f"Q{i}", "numeric_correct": n, "refused": r}
            for i, (n, r) in enumerate(zip(numeric, refused, strict=True))
        ],
    }


def test_comparison_shows_deltas_and_flips() -> None:
    md = render_comparison(
        (_retrieval(0.425, 0.181), _retrieval(0.625, 0.310, metadata_filter=True, decompose=True)),
        (_generation([False, True], [True, False]), _generation([True, True], [False, False])),
        "tuning.md",
    )
    assert "| Recall@10 | 42.5% | 62.5% | +20.0 pts |" in md
    assert "| MRR | 0.181 | 0.310 | +0.129 |" in md
    assert "metadata filter and decomposition per filing" in md
    assert "| Numeric correctness | 50.0% | 100.0% | +50.0 pts | 3 |" in md
    assert "| Refusal precision | 50.0% | 50.0% | +0.0 pts | 2 |" in md
    assert "Numeric: false → true for Q0; true → false for none." in md
    assert "Refused: false → true for none; true → false for Q0." in md
    assert "`tuning.md`" in md


def test_comparison_refuses_mismatched_datasets() -> None:
    other = _retrieval(0.5, 0.2) | {"dataset": "dev_v1@xyz"}
    with pytest.raises(ValueError, match="different datasets"):
        render_comparison((_retrieval(0.4, 0.1), other), None)
