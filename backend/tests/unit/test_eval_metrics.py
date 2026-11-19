from __future__ import annotations

import uuid

import pytest
import typer

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


def test_tuning_plan_is_pinned_to_the_dev_set() -> None:
    from docqa.evals.cli import _plan_dataset
    from docqa.evals.configs import CONFIG_DIR
    from docqa.evals.dataset import DATASET_DIR, DEFAULT_DATASET

    plan = load_ablations(CONFIG_DIR / "tuning.yaml")
    assert plan.dataset == "dev_v1.jsonl"
    assert plan.name == "tuning"
    # Every index the tuning variants use is built by the plan.
    built = {c.key for c in plan.indexes}
    assert {v.index_config for g in plan.groups.values() for v in g.values()} <= built

    assert _plan_dataset(plan, None).name == "dev_v1"
    assert _plan_dataset(plan, DATASET_DIR / "dev_v1.jsonl").name == "dev_v1"
    with pytest.raises(typer.Exit):
        _plan_dataset(plan, DEFAULT_DATASET)  # the held-out test set

    # Ablations are not pinned: they run on whatever dataset is given (qa_v1 by default).
    assert load_ablations().dataset is None
    assert _plan_dataset(load_ablations(), None).name == "qa_v1"


def test_dev_and_test_sets_do_not_share_questions() -> None:
    from docqa.evals.dataset import DATASET_DIR, DEFAULT_DATASET, Dataset, load_dataset

    test, dev = load_dataset(DEFAULT_DATASET), load_dataset(DATASET_DIR / "dev_v1.jsonl")
    assert len(dev.items) == 25
    assert {i.category for i in dev.items} == {i.category for i in test.items}
    assert not {i.id for i in dev.items} & {i.id for i in test.items}
    assert not {i.question.lower() for i in dev.items} & {i.question.lower() for i in test.items}

    # No dev source quote is a test source quote.
    def quotes(ds: Dataset) -> set[tuple[str, str]]:
        return {(s.doc, s.quote) for i in ds.items for s in i.sources}

    assert not quotes(dev) & quotes(test)
