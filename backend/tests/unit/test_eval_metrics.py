from __future__ import annotations

import uuid

from docqa.evals.configs import load_ablations, stable_hash
from docqa.evals.retrieval_eval import Metrics, QuestionResult, first_hit_rank, recall_at

A, B, C, D = (uuid.UUID(int=i) for i in range(1, 5))


def test_recall_counts_sources_hit_within_k() -> None:
    gold = [{A}, {C, D}]  # two sources; the second has two gold chunks
    ranked = [B, A, D]
    assert recall_at(gold, ranked, 1) == 0.0
    assert recall_at(gold, ranked, 2) == 0.5
    assert recall_at(gold, ranked, 3) == 1.0
    assert recall_at([], ranked, 3) == 0.0


def test_first_hit_rank_and_mrr() -> None:
    assert first_hit_rank([{A}], [B, C, A]) == 3
    assert first_hit_rank([{A}], [B]) is None
    results = [
        QuestionResult("q1", "table", [1], [A], 1, {5: 1.0}, 0.1),
        QuestionResult("q2", "table", [1], [B], 4, {5: 1.0}, 0.1),
        QuestionResult("q3", "factual", [0], [], None, {5: 0.0}, 0.1),
    ]
    m = Metrics.of(results, (5,))
    assert m.n == 3
    assert m.mrr == (1 + 0.25 + 0) / 3
    assert results[2].missing_gold
    assert not results[0].missing_gold


def test_ablation_plan_and_hashes() -> None:
    plan = load_ablations()
    assert {c.key for c in plan.indexes} >= {"section-512-64", "naive-512-64"}
    assert plan.base.top_n >= 10
    hybrid = plan.groups["search_mode"]["hybrid (RRF)"]
    assert hybrid.use_vector
    assert hybrid.use_keyword
    assert not hybrid.use_rerank
    assert plan.groups["table_aware"]["naive fixed windows"].index_config == "naive-512-64"
    assert stable_hash({"a": 1, "b": 2}) == stable_hash({"b": 2, "a": 1})
    assert stable_hash(plan.base) != stable_hash(hybrid)
