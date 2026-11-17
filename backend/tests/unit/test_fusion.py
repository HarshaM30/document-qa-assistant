from __future__ import annotations

import pytest

from docqa.retrieval.fusion import reciprocal_rank_fusion


def test_rrf_scores_match_hand_computation() -> None:
    fused = dict(reciprocal_rank_fusion([["a", "b", "c"], ["c", "a", "d"]], k=60))
    assert fused["a"] == pytest.approx(1 / 61 + 1 / 62)
    assert fused["c"] == pytest.approx(1 / 63 + 1 / 61)
    assert fused["b"] == pytest.approx(1 / 62)
    assert fused["d"] == pytest.approx(1 / 63)


def test_rrf_orders_by_fused_score() -> None:
    ranked = [doc for doc, _ in reciprocal_rank_fusion([["a", "b", "c"], ["c", "a", "d"]], k=60)]
    # a: 1/61 + 1/62 > c: 1/61 + 1/63 > b: 1/62 > d: 1/63
    assert ranked == ["a", "c", "b", "d"]


def test_item_in_both_lists_beats_top_of_one() -> None:
    # "x" is second in both lists; "a" and "b" are each first in only one.
    ranked = [d for d, _ in reciprocal_rank_fusion([["a", "x"], ["b", "x"]], k=60)]
    assert ranked[0] == "x"


def test_small_k_rewards_top_ranks_more() -> None:
    rankings = [["a", "b", "c", "d"], ["d", "e", "f", "a"]]
    assert reciprocal_rank_fusion(rankings, k=0)[0][0] == "a"  # 1/1 + 1/4 = 1.25 vs d 1.25
    scores = dict(reciprocal_rank_fusion(rankings, k=0))
    assert scores["a"] == pytest.approx(1.25)
    assert scores["d"] == pytest.approx(1.25)


def test_ties_keep_first_seen_order_and_single_list_is_unchanged() -> None:
    assert [d for d, _ in reciprocal_rank_fusion([["a", "b"], ["b", "a"]])] == ["a", "b"]
    assert [d for d, _ in reciprocal_rank_fusion([["z", "y", "x"]])] == ["z", "y", "x"]


def test_empty_and_invalid() -> None:
    assert reciprocal_rank_fusion([]) == []
    assert reciprocal_rank_fusion([[], []]) == []
    with pytest.raises(ValueError, match="non-negative"):
        reciprocal_rank_fusion([["a"]], k=-1)
