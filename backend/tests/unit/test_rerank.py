from __future__ import annotations

import pytest

from docqa.config import Settings
from docqa.retrieval.rerank import get_reranker, rerank_order


def test_rerank_order_sorts_by_score_and_keeps_ties_stable() -> None:
    assert rerank_order([0.1, 2.0, -3.0, 2.0]) == [1, 3, 0, 2]
    assert rerank_order([]) == []


@pytest.fixture(scope="module")
def reranker():  # type: ignore[no-untyped-def]
    return get_reranker(Settings())


def test_cross_encoder_moves_relevant_passage_to_top(reranker) -> None:  # type: ignore[no-untyped-def]
    query = "Where is the company's largest supplier located?"
    passages = [  # in fused order, relevant one last
        "The company operates 42 retail stores in North America and Europe.",
        "Revenue by segment: Footwear 12,400; Apparel 8,300 (in thousands).",
        "The company's largest supplier is located in Portugal.",
    ]
    scores = reranker.score(query, passages)
    assert len(scores) == 3
    assert rerank_order(scores)[0] == 2
    assert reranker.score(query, []) == []


def test_cross_encoder_scores_unrelated_text_low(reranker) -> None:  # type: ignore[no-untyped-def]
    [score] = reranker.score(
        "Who won the 2022 FIFA World Cup?",
        ["Revenue by segment: Footwear 12,400; Apparel 8,300 (in thousands)."],
    )
    assert score < Settings().refusal_min_rerank_score
