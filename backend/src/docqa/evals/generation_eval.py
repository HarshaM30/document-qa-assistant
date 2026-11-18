"""Generation eval on the final config: answer, judge, checkpoint, and score.

Each question goes through two LLM stages, answer and then faithfulness judge, and the
record is appended to a JSONL checkpoint after each stage. Records are keyed by
(question id, run hash); the run hash covers the retrieval config, models, and prompts, so
changing any of them starts a fresh checkpoint instead of mixing results.

If one model's daily budget runs out, the other keeps going where it can (answers continue
without judging, or pending answers get judged), then the run stops and resumes from the
checkpoint on the next invocation.
"""

from __future__ import annotations

import json
import logging
import re
import statistics
import uuid
from collections import defaultdict
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from docqa.config import REPO_ROOT
from docqa.evals.budget import BudgetExhaustedError
from docqa.evals.client import BudgetedClient
from docqa.evals.configs import GenerationConfig, stable_hash
from docqa.evals.dataset import Category, Dataset, NumericFact, QAItem
from docqa.evals.judge import JUDGE_SYSTEM, Verdict, judge_messages, parse_verdict
from docqa.evals.reports import pct, table
from docqa.evals.retrieval_eval import GoldIndex
from docqa.evals.xbrl_check import UNITS
from docqa.generation.chain import to_litellm_messages
from docqa.generation.citations import parse_markers, resolve_citations
from docqa.generation.llm import LLMSpec
from docqa.generation.prompts import (
    REFUSAL_SENTENCE,
    SYSTEM_PROMPT,
    USER_PROMPT,
    answer_prompt,
    format_context,
)
from docqa.generation.refusal import is_refusal, pre_generation_gate
from docqa.retrieval.retriever import Retriever

log = logging.getLogger(__name__)

CHECKPOINT_DIR = REPO_ROOT / "evals" / "checkpoints"
NUMERIC_TOLERANCE = 0.01  # relative; allows "$416.2 billion" for 416,161 (millions)


def run_hash(config: GenerationConfig, answer: LLMSpec, judge: LLMSpec) -> str:
    return stable_hash(
        {
            "config": config.hash,
            "answer": [answer.litellm_model, answer.temperature, answer.max_tokens,
                       answer.reasoning_effort],
            "judge": [judge.litellm_model, judge.temperature, judge.max_tokens],
            "prompts": stable_hash([SYSTEM_PROMPT, USER_PROMPT, REFUSAL_SENTENCE, JUDGE_SYSTEM]),
        }
    )  # fmt: skip


def checkpoint_path(dataset: Dataset, config: GenerationConfig, hash_: str) -> Path:
    return CHECKPOINT_DIR / f"{dataset.name}-{config.name}-{hash_}.jsonl"


class Checkpoint:
    """Append-only JSONL; the last line for a key wins."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.records: dict[str, dict[str, Any]] = {}
        if path.exists():
            for line in path.read_text().splitlines():
                if line.strip():
                    record = json.loads(line)
                    self.records[record["key"]] = record

    def get(self, key: str) -> dict[str, Any] | None:
        return self.records.get(key)

    def put(self, record: dict[str, Any]) -> None:
        self.records[record["key"]] = record
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


@dataclass(frozen=True)
class _StoredPassage:
    label: str
    text: str


def stored_context(record: dict[str, Any]) -> str:
    return format_context([_StoredPassage(p["label"], p["text"]) for p in record["passages"]])


def needs_judge(record: dict[str, Any]) -> bool:
    return not record["refused"] and record.get("judge") is None


@dataclass
class Generator:
    db: AsyncSession
    retriever: Retriever
    config: GenerationConfig
    client: BudgetedClient
    answer_spec: LLMSpec
    judge_spec: LLMSpec
    workspace_id: uuid.UUID
    gold: GoldIndex
    hash: str

    def key(self, item: QAItem) -> str:
        return f"{item.id}:{self.hash}"

    async def answer(self, item: QAItem) -> dict[str, Any]:
        passages = await self.retriever.retrieve(
            self.db, self.workspace_id, item.question, self.config.retrieval
        )
        gold_sets = await self.gold.for_item(self.db, item)
        await self.db.rollback()  # don't hold a connection during the LLM call
        gate = pre_generation_gate(passages, self.config.refusal_min_rerank_score)
        usage = None
        if gate.refuse:
            text = REFUSAL_SENTENCE
        else:
            prompt = answer_prompt().invoke(
                {"context": format_context(passages), "question": item.question}
            )
            messages = to_litellm_messages(prompt.to_messages())
            completion = await self.client.complete(self.answer_spec, messages)
            text = completion.text
            usage = {
                "prompt_tokens": completion.prompt_tokens,
                "completion_tokens": completion.completion_tokens,
            }
        citations = resolve_citations(text, passages)
        return {
            "key": self.key(item),
            "item_id": item.id,
            "question": item.question,
            "run_hash": self.hash,
            "answer_model": self.answer_spec.litellm_model,
            "judge_model": self.judge_spec.litellm_model,
            "passages": [
                {
                    "chunk_id": str(p.chunk_id),
                    "label": p.label,
                    "text": p.text,
                    "is_table": p.is_table,
                    "rerank_score": p.rerank_score,
                }
                for p in passages
            ],
            "gold_chunk_ids": [sorted(str(c) for c in g) for g in gold_sets],
            "gate_refused": gate.refuse,
            "best_rerank_score": gate.best_score,
            "answer": text,
            "refused": gate.refuse or is_refusal(text),
            "cited_chunk_ids": [str(c.chunk_id) for c in citations],
            "answer_usage": usage,
            "judge": None,
            "judge_usage": None,
        }

    async def judge(self, record: dict[str, Any]) -> dict[str, Any]:
        messages = judge_messages(stored_context(record), record["question"], record["answer"])
        completion = await self.client.complete(self.judge_spec, messages)
        verdict = parse_verdict(completion.text)
        return record | {
            "judge": verdict.to_json(),
            "judge_usage": {
                "prompt_tokens": completion.prompt_tokens,
                "completion_tokens": completion.completion_tokens,
            },
        }


@dataclass
class RunOutcome:
    completed: int
    total: int
    stopped: dict[str, str] = field(default_factory=dict)  # model -> reason

    @property
    def finished(self) -> bool:
        return self.completed == self.total


def is_complete(record: dict[str, Any] | None) -> bool:
    return record is not None and not needs_judge(record)


async def run_generation(
    gen: Generator,
    items: Sequence[QAItem],
    checkpoint: Checkpoint,
    on_record: Callable[[dict[str, Any]], None] = lambda r: None,
) -> RunOutcome:
    stopped: dict[str, str] = {}
    answer_model, judge_model = gen.answer_spec.litellm_model, gen.judge_spec.litellm_model
    for item in items:
        record = checkpoint.get(gen.key(item))
        if record is not None and record.get("question") != item.question:
            record = None  # the question was edited since this record was written
        if record is None:
            if answer_model in stopped:
                continue
            try:
                record = await gen.answer(item)
            except BudgetExhaustedError as exc:
                stopped[answer_model] = exc.reason
                continue
            checkpoint.put(record)
            on_record(record)
        if needs_judge(record) and judge_model not in stopped:
            try:
                record = await gen.judge(record)
            except BudgetExhaustedError as exc:
                stopped[judge_model] = exc.reason
                continue
            checkpoint.put(record)
            on_record(record)
        if len(stopped) == 2:
            break
    completed = sum(1 for i in items if is_complete(checkpoint.get(gen.key(i))))
    return RunOutcome(completed, len(items), stopped)


# --- Scoring (no LLM) --------------------------------------------------------------------

_MARKERS = re.compile(r"\[\s*\d+(?:\s*,\s*\d+)*\s*(?:\u2020[^\]]*)?\]")
_NUMBER = re.compile(
    r"(?<![\w.])(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)\s*"
    r"(%|percent\b|thousand\b|million\b|billion\b|trillion\b)?",
    re.I,
)
_SCALE = {"thousand": 1e3, "million": 1e6, "billion": 1e9, "trillion": 1e12}


def extract_numbers(text: str) -> list[tuple[float, float]]:
    """(number as written, number with its scale word applied) for each number in the text."""
    out = []
    for match in _NUMBER.finditer(_MARKERS.sub(" ", text)):
        value = float(match.group(1).replace(",", ""))
        word = (match.group(2) or "").lower()
        out.append((value, value * _SCALE.get(word, 1.0)))
    return out


def _close(a: float, b: float) -> bool:
    return abs(a - b) <= NUMERIC_TOLERANCE * max(abs(a), abs(b), 1e-9)


def states_number(answer: str, fact: NumericFact) -> bool:
    """True if the answer states the fact's value, in its own unit or scaled (e.g. billions)."""
    scale = UNITS.get(fact.unit, (1.0, None))[0]
    gold_scaled = fact.value * scale
    return any(
        _close(raw, fact.value) or _close(scaled, gold_scaled)
        for raw, scaled in extract_numbers(answer)
    )


def cited_chunk_ids(record: dict[str, Any]) -> list[str]:
    """Chunks the answer cites, re-derived from its text so parser fixes apply on re-scoring."""
    passages = record["passages"]
    return [
        passages[m - 1]["chunk_id"]
        for m in parse_markers(record["answer"])
        if 1 <= m <= len(passages)
    ]


@dataclass(frozen=True)
class ItemScore:
    item_id: str
    category: str
    answerable: bool
    refused: bool
    gate_refused: bool
    numeric_correct: bool | None  # None: no numeric facts
    citation_correct: bool | None  # None: unanswerable or refused
    gold_retrieved: bool | None
    faithful: bool | None  # None: not judged (refused) or judge unparsed
    judged: bool


def score_record(item: QAItem, record: dict[str, Any]) -> ItemScore:
    refused = bool(record["refused"])
    gold = {c for group in record["gold_chunk_ids"] for c in group}
    retrieved = {p["chunk_id"] for p in record["passages"]}
    numeric = None
    if item.answerable and item.numeric:
        numeric = not refused and all(states_number(record["answer"], f) for f in item.numeric)
    citation = None
    if item.answerable and not refused:
        citation = bool(gold & set(cited_chunk_ids(record)))
    verdict = Verdict.from_json(record["judge"]) if record.get("judge") else None
    return ItemScore(
        item_id=item.id,
        category=item.category.value,
        answerable=item.answerable,
        refused=refused,
        gate_refused=bool(record["gate_refused"]),
        numeric_correct=numeric,
        citation_correct=citation,
        gold_retrieved=bool(gold & retrieved) if item.answerable else None,
        faithful=verdict.faithful if verdict else None,
        judged=verdict is not None,
    )


def _rate(values: Sequence[bool | None]) -> tuple[float | None, int]:
    known = [v for v in values if v is not None]
    return (statistics.fmean(known) if known else None), len(known)


def summarize(scores: Sequence[ItemScore]) -> dict[str, Any]:
    unanswerable = [s for s in scores if not s.answerable]
    answerable = [s for s in scores if s.answerable]
    tp = sum(1 for s in unanswerable if s.refused)
    fp = sum(1 for s in answerable if s.refused)
    fn = len(unanswerable) - tp
    numeric, n_numeric = _rate([s.numeric_correct for s in scores])
    citation, n_citation = _rate([s.citation_correct for s in scores])
    faithful, n_faithful = _rate([s.faithful for s in scores])
    retrieved, n_retrieved = _rate([s.gold_retrieved for s in scores])
    return {
        "questions": len(scores),
        "numeric_accuracy": numeric,
        "numeric_n": n_numeric,
        "citation_accuracy": citation,
        "citation_n": n_citation,
        "gold_in_context": retrieved,
        "gold_in_context_n": n_retrieved,
        "refusal_precision": tp / (tp + fp) if tp + fp else None,
        "refusal_recall": tp / (tp + fn) if tp + fn else None,
        "refusals": {"true_positive": tp, "false_positive": fp, "false_negative": fn},
        "gate_refusals": sum(1 for s in scores if s.gate_refused),
        "faithfulness": faithful,
        "faithfulness_n": n_faithful,
        "judge_unparsed": sum(1 for s in scores if s.judged and s.faithful is None),
    }


def score_run(
    dataset: Dataset, checkpoint: Checkpoint, hash_: str
) -> tuple[list[ItemScore], list[str]]:
    """Scores for completed items, plus the ids still pending."""
    scores, pending = [], []
    for item in dataset.items:
        record = checkpoint.get(f"{item.id}:{hash_}")
        if is_complete(record) and record is not None and record["question"] == item.question:
            scores.append(score_record(item, record))
        else:
            pending.append(item.id)
    return scores, pending


def _usage_totals(checkpoint: Checkpoint, hash_: str) -> dict[str, dict[str, int]]:
    totals: dict[str, dict[str, int]] = defaultdict(lambda: {"requests": 0, "tokens": 0})
    for record in checkpoint.records.values():
        if record.get("run_hash") != hash_:
            continue
        for stage, model_key in (("answer_usage", "answer_model"), ("judge_usage", "judge_model")):
            usage = record.get(stage)
            if usage:
                t = totals[record[model_key]]
                t["requests"] += 1
                t["tokens"] += usage["prompt_tokens"] + usage["completion_tokens"]
    return dict(totals)


def render_generation(
    summary: dict[str, Any],
    by_category: dict[str, dict[str, Any]],
    scores: Sequence[ItemScore],
    pending: Sequence[str],
    meta: dict[str, Any],
) -> str:
    status = (
        "complete"
        if not pending
        else f"partial: {len(scores)} of {len(scores) + len(pending)} questions"
    )
    rf = summary["refusals"]
    lines = [
        "# Generation eval",
        "",
        f"Config `{meta['config']}` (run `{meta['run_hash']}`); answer model "
        f"`{meta['answer_model']}`, judge `{meta['judge_model']}`. Status: **{status}**.",
        "",
        table(
            ["Metric", "Value", "n", "Definition"],
            [
                ["Numeric correctness", pct(summary["numeric_accuracy"]), summary["numeric_n"],
                 "every gold number stated (±1%, any scale); refusals count as wrong"],
                ["Citation correctness", pct(summary["citation_accuracy"]), summary["citation_n"],
                 "a cited passage contains the gold quote (answered questions)"],
                ["Gold passage in context", pct(summary["gold_in_context"]),
                 summary["gold_in_context_n"], "retrieval put a gold chunk in the prompt"],
                ["Refusal precision", pct(summary["refusal_precision"]),
                 rf["true_positive"] + rf["false_positive"], "refusals that were unanswerable"],
                ["Refusal recall", pct(summary["refusal_recall"]),
                 rf["true_positive"] + rf["false_negative"], "unanswerables that were refused"],
                ["Faithfulness (judge)", pct(summary["faithfulness"]), summary["faithfulness_n"],
                 "judge found every claim supported by the passages"],
            ],
        ),
        "",
        f"Refused before calling the LLM (rerank gate): {summary['gate_refusals']}. "
        f"Unparsed judge replies: {summary['judge_unparsed']}.",
        "",
        "## By category",
        "",
        table(
            ["Category", "n", "Numeric", "Citation", "Refused", "Faithful"],
            [
                [c, v["questions"], pct(v["numeric_accuracy"]), pct(v["citation_accuracy"]),
                 v["refused"], pct(v["faithfulness"])]
                for c, v in by_category.items()
            ],
        ),
        "",
        "## Per question",
        "",
        table(
            ["Question", "Category", "Refused", "Numeric", "Citation", "Faithful"],
            [
                [s.item_id, s.category, "yes" if s.refused else "no",
                 _mark(s.numeric_correct), _mark(s.citation_correct), _mark(s.faithful)]
                for s in scores
            ],
        ),
    ]  # fmt: skip
    if meta.get("usage"):
        lines += [
            "",
            "## LLM usage (this run, all days)",
            "",
            table(
                ["Model", "Requests", "Tokens"],
                [[m, u["requests"], f"{u['tokens']:,}"] for m, u in meta["usage"].items()],
            ),
        ]
    if pending:
        lines += ["", f"Pending: {', '.join(pending)}"]
    return "\n".join(lines) + "\n"


def _mark(value: bool | None) -> str:
    return {True: "✓", False: "✗", None: "—"}[value]


def generation_report(
    dataset: Dataset,
    checkpoint: Checkpoint,
    config: GenerationConfig,
    hash_: str,
    answer_model: str,
    judge_model: str,
) -> tuple[dict[str, Any], str]:
    scores, pending = score_run(dataset, checkpoint, hash_)
    summary = summarize(scores)
    by_category = {}
    for category in Category:
        group = [s for s in scores if s.category == category.value]
        if group:
            by_category[category.value] = summarize(group) | {
                "refused": sum(1 for s in group if s.refused)
            }
    meta = {
        "config": config.name,
        "config_hash": config.hash,
        "run_hash": hash_,
        "answer_model": answer_model,
        "judge_model": judge_model,
        "checkpoint": str(checkpoint.path.relative_to(REPO_ROOT))
        if checkpoint.path.is_relative_to(REPO_ROOT)
        else str(checkpoint.path),
        "usage": _usage_totals(checkpoint, hash_),
    }
    data = meta | {
        "complete": not pending,
        "pending": pending,
        "summary": summary,
        "by_category": by_category,
        "items": [s.__dict__ for s in scores],
    }
    return data, render_generation(summary, by_category, scores, pending, meta)
