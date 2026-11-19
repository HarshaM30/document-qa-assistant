"""Before/after comparison of two retrieval reports and two generation reports (no LLM).

Reads the JSON written next to each markdown report, so a comparison can be regenerated at
any time from committed files.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from docqa.evals.reports import pct, table

_GENERATION_METRICS: list[tuple[str, str]] = [
    ("numeric_accuracy", "Numeric correctness"),
    ("citation_accuracy", "Citation correctness"),
    ("gold_in_context", "Gold passage in context"),
    ("refusal_precision", "Refusal precision"),
    ("refusal_recall", "Refusal recall"),
    ("faithfulness", "Faithfulness (judge)"),
]


def _delta(before: float | None, after: float | None, fmt: Callable[[float], str]) -> str:
    if before is None or after is None:
        return "n/a"
    diff = after - before
    return ("+" if diff >= 0 else "-") + fmt(abs(diff))


def _points(x: float) -> str:
    return f"{x * 100:.1f} pts"


def _retrieval_rows(before: dict[str, Any], after: dict[str, Any]) -> list[list[Any]]:
    rows = []
    for key, label in (("5", "Recall@5"), ("10", "Recall@10")):
        b, a = before["overall"]["recall"][key], after["overall"]["recall"][key]
        rows.append([label, pct(b), pct(a), _delta(b, a, _points)])
    b, a = before["overall"]["mrr"], after["overall"]["mrr"]
    rows.append(["MRR", f"{b:.3f}", f"{a:.3f}", _delta(b, a, lambda x: f"{x:.3f}")])
    b, a = before["mean_seconds"], after["mean_seconds"]
    rows.append(
        ["Latency (mean)", f"{b * 1000:.0f} ms", f"{a * 1000:.0f} ms", f"{(a - b) * 1000:+.0f} ms"]
    )
    return rows


def _category_rows(before: dict[str, Any], after: dict[str, Any]) -> list[list[Any]]:
    rows = []
    for category, b in before["by_category"].items():
        a = after["by_category"].get(category)
        if a is None:
            continue
        rows.append(
            [
                category,
                b["n"],
                f"{pct(b['recall']['10'])} → {pct(a['recall']['10'])}",
                f"{b['mrr']:.3f} → {a['mrr']:.3f}",
            ]
        )
    return rows


def _n(summary: dict[str, Any], key: str) -> Any:
    refusals = summary.get("refusals", {})
    if key == "refusal_precision":
        return refusals.get("true_positive", 0) + refusals.get("false_positive", 0)
    if key == "refusal_recall":
        return refusals.get("true_positive", 0) + refusals.get("false_negative", 0)
    base = key.removesuffix("_accuracy")  # numeric_accuracy -> numeric_n
    return summary.get(f"{base}_n", summary.get("questions"))


def _generation_rows(before: dict[str, Any], after: dict[str, Any]) -> list[list[Any]]:
    rows = []
    b_sum, a_sum = before["summary"], after["summary"]
    for key, label in _GENERATION_METRICS:
        b, a = b_sum.get(key), a_sum.get(key)
        n = _n(a_sum, key)
        rows.append([label, pct(b), pct(a), _delta(b, a, _points), n])
    return rows


def _flips(
    before: dict[str, Any], after: dict[str, Any], field: str
) -> tuple[list[str], list[str]]:
    """Question ids that went from wrong to right, and from right to wrong, on `field`."""
    b_items = {i["item_id"]: i for i in before["items"]}
    gained, lost = [], []
    for item in after["items"]:
        prev = b_items.get(item["item_id"])
        if prev is None:
            continue
        b, a = prev.get(field), item.get(field)
        if b is False and a is True:
            gained.append(item["item_id"])
        elif b is True and a is False:
            lost.append(item["item_id"])
    return gained, lost


def render_comparison(
    retrieval: tuple[dict[str, Any], dict[str, Any]],
    generation: tuple[dict[str, Any], dict[str, Any]] | None,
    tuning_report: str | None = None,
) -> str:
    r_before, r_after = retrieval
    if r_before.get("dataset") != r_after.get("dataset"):
        raise ValueError("retrieval reports are for different datasets")
    lines = [
        "# Retrieval improvements: before and after (Milestone 5b)",
        "",
        f"Held-out test set `{r_after['dataset']}`, run once with the final configuration. "
        "Every change was chosen on the separate dev set"
        + (f" (`{tuning_report}`)" if tuning_report else "")
        + "; none was tuned on this set.",
        "",
        f"Before: `{r_before['config']['index_config']}`, hybrid + rerank "
        f"(report `{r_before['created_at']}`). After: the same index and pools plus "
        + _stage_list(r_after["config"])
        + f" (report `{r_after['created_at']}`).",
        "",
        "## Retrieval (no LLM)",
        "",
        table(["Metric", "Before", "After", "Change"], _retrieval_rows(r_before, r_after)),
        "",
        table(["Category", "n", "Recall@10", "MRR"], _category_rows(r_before, r_after)),
    ]
    if generation is not None:
        g_before, g_after = generation
        if g_before.get("dataset") != g_after.get("dataset"):
            raise ValueError("generation reports are for different datasets")
        lines += [
            "",
            "## Generation",
            "",
            f"Answer model `{g_after['answer_model']}`, judge `{g_after['judge_model']}`. "
            f"Runs `{g_before['run_hash']}` (before) and `{g_after['run_hash']}` (after).",
            "",
            table(
                ["Metric", "Before", "After", "Change", "n (after)"],
                _generation_rows(g_before, g_after),
            ),
        ]
        for field, label in (("numeric_correct", "Numeric"), ("refused", "Refused")):
            gained, lost = _flips(g_before, g_after, field)
            if gained or lost:
                lines += [
                    "",
                    f"{label}: false → true for {', '.join(gained) or 'none'}; "
                    f"true → false for {', '.join(lost) or 'none'}.",
                ]
    return "\n".join(lines) + "\n"


def _stage_list(config: dict[str, Any]) -> str:
    parts = []
    if config.get("metadata_filter"):
        parts.append("company/fiscal-year metadata filter")
    if config.get("decompose"):
        parts.append(f"decomposition per {config.get('decompose_by', 'filing')}")
    return " and ".join(parts) or "no new stages"
