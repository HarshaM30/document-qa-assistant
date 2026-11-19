"""Retrieval ablations (no LLM): run every variant in `evals/configs/ablations.yaml`."""

from __future__ import annotations

import logging
import uuid
from dataclasses import asdict
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from docqa.evals.configs import AblationPlan
from docqa.evals.dataset import Dataset
from docqa.evals.reports import pct, table
from docqa.evals.retrieval_eval import GoldIndex, RetrievalRun, evaluate_retrieval
from docqa.retrieval.retriever import RetrievalConfig, Retriever

log = logging.getLogger(__name__)


class GoldCache:
    def __init__(self, documents: dict[str, uuid.UUID]) -> None:
        self.documents = documents
        self._by_config: dict[str, GoldIndex] = {}

    def get(self, index_config: str) -> GoldIndex:
        if index_config not in self._by_config:
            self._by_config[index_config] = GoldIndex(self.documents, index_config)
        return self._by_config[index_config]


async def run_ablations(
    db: AsyncSession,
    retriever: Retriever,
    workspace_id: uuid.UUID,
    dataset: Dataset,
    plan: AblationPlan,
    gold: GoldCache,
) -> dict[str, dict[str, RetrievalRun]]:
    runs: dict[str, dict[str, RetrievalRun]] = {}
    done: dict[RetrievalConfig, RetrievalRun] = {}  # identical variants run once
    for group, variants in plan.groups.items():
        runs[group] = {}
        for name, config in variants.items():
            if config not in done:
                log.info("ablation %s / %s", group, name)
                done[config] = await evaluate_retrieval(
                    db, retriever, workspace_id, dataset, config, gold.get(config.index_config)
                )
            runs[group][name] = done[config]
    return runs


def _metric_row(name: str, run: RetrievalRun) -> list[Any]:
    m = run.overall
    return [
        name,
        *(pct(m.recall[k]) for k in run.ks),
        f"{m.mrr:.3f}",
        f"{run.mean_seconds * 1000:.0f} ms",
    ]


def _headers(ks: tuple[int, ...]) -> list[str]:
    return ["Variant", *(f"Recall@{k}" for k in ks), "MRR", "Latency (mean)"]


def run_summary(run: RetrievalRun) -> dict[str, Any]:
    return {
        "config": asdict(run.config),
        "overall": asdict(run.overall),
        "by_category": {c: asdict(m) for c, m in run.by_category.items()},
        "mean_seconds": round(run.mean_seconds, 4),
        "missing_gold": run.missing_gold,
        "questions": [
            {
                "id": r.item_id,
                "category": r.category,
                "gold_chunks": r.gold_counts,
                "first_hit_rank": r.first_hit,
                "recall": r.recall,
            }
            for r in run.results
        ],
    }


def render_retrieval(run: RetrievalRun, title: str = "Retrieval eval") -> str:
    cfg = run.config
    stages = [
        s
        for s, on in (
            ("vector", cfg.use_vector),
            ("keyword", cfg.use_keyword),
            ("rerank", cfg.use_rerank),
            ("metadata filter", cfg.metadata_filter),
            ("decomposition", cfg.decompose),
        )
        if on
    ]
    lines = [
        f"# {title}",
        "",
        f"Index `{cfg.index_config}`, stages: {' + '.join(stages)}, candidates "
        f"{cfg.vector_k} vector / {cfg.keyword_k} keyword / {cfg.rerank_candidates} reranked, "
        f"{run.overall.n} answerable questions. No LLM calls.",
        "",
        table(_headers(run.ks), [_metric_row("overall", run)]),
        "",
        "## By category",
        "",
        table(
            ["Category", "n", *(f"Recall@{k}" for k in run.ks), "MRR"],
            [
                [c, m.n, *(pct(m.recall[k]) for k in run.ks), f"{m.mrr:.3f}"]
                for c, m in run.by_category.items()
            ],
        ),
    ]
    misses = [r for r in run.results if r.recall[max(run.ks)] < 1.0]
    if misses:
        lines += [
            "",
            f"## Not fully retrieved in the top {max(run.ks)}",
            "",
            table(
                ["Question", "Category", "First gold rank", f"Recall@{max(run.ks)}"],
                [
                    [r.item_id, r.category, r.first_hit or "—", pct(r.recall[max(run.ks)])]
                    for r in misses
                ],
            ),
        ]
    if run.missing_gold:
        lines += ["", f"Questions with a source quote in no chunk: {', '.join(run.missing_gold)}"]
    return "\n".join(lines) + "\n"


_GROUP_TITLES = {
    "chunk_size": "Chunk size (section-aware, hybrid + rerank)",
    "table_aware": "Table-aware vs naive chunking (512 tokens, hybrid + rerank)",
    "search_mode": "Vector vs keyword vs hybrid (no rerank)",
    "rerank": "Cross-encoder rerank",
}


def render_ablations(
    runs: dict[str, dict[str, RetrievalRun]],
    titles: dict[str, str] | None = None,
    heading: str = "Retrieval ablations",
) -> str:
    titles = _GROUP_TITLES | (titles or {})
    any_run = next(iter(next(iter(runs.values())).values()))
    lines = [
        f"# {heading}",
        "",
        f"{any_run.overall.n} answerable questions; every variant retrieves the top "
        f"{any_run.config.top_n}. No LLM calls. Latency is per question on this machine, "
        "including query embedding and reranking.",
    ]
    for group, variants in runs.items():
        lines += [
            "",
            f"## {titles.get(group, group)}",
            "",
            table(
                _headers(any_run.ks),
                [_metric_row(name, run) for name, run in variants.items()],
            ),
        ]
        missing = sorted({q for run in variants.values() for q in run.missing_gold})
        if missing:
            lines += ["", f"Quote not found in any chunk of some variant: {', '.join(missing)}"]
    return "\n".join(lines) + "\n"


def ablations_summary(runs: dict[str, dict[str, RetrievalRun]]) -> dict[str, Any]:
    return {
        group: {name: run_summary(run) for name, run in variants.items()}
        for group, variants in runs.items()
    }
