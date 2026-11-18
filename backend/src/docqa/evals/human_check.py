"""Human check of the faithfulness judge: export judged answers, then measure agreement.

`export_markdown` writes a file with one section per answer: question, answer, the
passages the model saw, and the judge's verdict, followed by two checkboxes. A reviewer
ticks "Agree" or "Disagree"; `parse_marks` reads them back and `agreement` reports the
agreement rate and Cohen's kappa between judge and human labels.
"""

from __future__ import annotations

import random
import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from docqa.config import REPO_ROOT
from docqa.evals.judge import Verdict

HUMAN_CHECK_DIR = REPO_ROOT / "evals" / "human_check"
DEFAULT_SAMPLE = 20

_ITEM = re.compile(r"<!-- item: (?P<id>[\w-]+) judge: (?P<verdict>\w+) -->")
_AGREE = re.compile(r"^\s*[-*]\s*\[(?P<mark>[ xX])\]\s*Agree\b", re.M)
_DISAGREE = re.compile(r"^\s*[-*]\s*\[(?P<mark>[ xX])\]\s*Disagree\b", re.M)


def select_records(
    records: Sequence[dict[str, Any]], n: int, seed: int = 0
) -> list[dict[str, Any]]:
    """Up to n judged answers: every 'unfaithful' verdict, then a seeded sample of the rest."""
    judged = [
        r for r in records if r.get("judge") and Verdict.from_json(r["judge"]).faithful is not None
    ]
    unfaithful = [r for r in judged if Verdict.from_json(r["judge"]).faithful is False]
    faithful = [r for r in judged if Verdict.from_json(r["judge"]).faithful]
    picked = unfaithful[:n]
    rest = sorted(faithful, key=lambda r: r["item_id"])
    random.Random(seed).shuffle(rest)
    picked += rest[: n - len(picked)]
    return sorted(picked, key=lambda r: r["item_id"])


def _quote(text: str) -> str:
    return "\n".join(f"> {line}" if line else ">" for line in text.strip().splitlines())


def export_markdown(records: Sequence[dict[str, Any]], dataset_version: str, run_hash: str) -> str:
    lines = [
        "# Human check: faithfulness judge",
        "",
        f"Dataset `{dataset_version}`, run `{run_hash}`. {len(records)} judged answers.",
        "",
        "For each answer, read the passages and decide whether the judge's verdict is right:",
        "*faithful* means every claim in the answer is supported by the passages (simple "
        "arithmetic allowed); *unfaithful* means at least one claim is not.",
        "",
        "Mark exactly one box per answer by changing `[ ]` to `[x]`, then run "
        "`make eval-agreement`.",
    ]
    for n, record in enumerate(records, start=1):
        verdict = Verdict.from_json(record["judge"])
        cited = set(record["cited_chunk_ids"])
        lines += [
            "",
            "---",
            "",
            f"<!-- item: {record['item_id']} judge: {verdict.label} -->",
            f"## {n}. {record['item_id']}: {record['question']}",
            "",
            "**Answer**",
            "",
            _quote(record["answer"]),
            "",
            f"**Judge verdict: {verdict.label}.** {verdict.reason}",
        ]
        if verdict.unsupported_claims:
            lines += ["", "Unsupported claims named by the judge:"]
            lines += [f"- {c}" for c in verdict.unsupported_claims]
        lines += [
            "",
            "**Your call**",
            "",
            "- [ ] Agree with the judge",
            "- [ ] Disagree with the judge",
            "",
            "Notes:",
            "",
            "<details><summary>Passages the model saw (cited ones marked ★)</summary>",
            "",
        ]
        for i, p in enumerate(record["passages"], start=1):
            star = " ★" if p["chunk_id"] in cited else ""
            lines += [f"**[{i}]{star} {p['label']}**", "", _quote(p["text"]), ""]
        lines += ["</details>"]
    return "\n".join(lines) + "\n"


@dataclass(frozen=True)
class Mark:
    item_id: str
    judge_faithful: bool
    agree: bool | None  # None: unmarked or both boxes ticked

    @property
    def human_faithful(self) -> bool | None:
        if self.agree is None:
            return None
        return self.judge_faithful if self.agree else not self.judge_faithful


def parse_marks(markdown: str) -> list[Mark]:
    matches = list(_ITEM.finditer(markdown))
    marks = []
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(markdown)
        body = markdown[match.end() : end]
        agree_box, disagree_box = _AGREE.search(body), _DISAGREE.search(body)
        agree = bool(agree_box and agree_box["mark"].strip())
        disagree = bool(disagree_box and disagree_box["mark"].strip())
        choice = agree if agree != disagree else None
        marks.append(Mark(match["id"], match["verdict"] == "faithful", choice))
    return marks


@dataclass(frozen=True)
class Agreement:
    marked: int
    unmarked: list[str]
    agreed: int
    rate: float | None
    kappa: float | None
    confusion: dict[str, int]  # judge/human label pairs


def cohens_kappa(pairs: Sequence[tuple[bool, bool]]) -> float | None:
    """Cohen's kappa for two raters' binary labels; None if undefined (chance agreement 1)."""
    n = len(pairs)
    if not n:
        return None
    observed = sum(1 for a, b in pairs if a == b) / n
    p_a = sum(1 for a, _ in pairs if a) / n
    p_b = sum(1 for _, b in pairs if b) / n
    expected = p_a * p_b + (1 - p_a) * (1 - p_b)
    if expected >= 1.0:
        return None
    return (observed - expected) / (1 - expected)


def agreement(marks: Sequence[Mark]) -> Agreement:
    done = [m for m in marks if m.agree is not None]
    pairs = [(m.judge_faithful, bool(m.human_faithful)) for m in done]
    label = {True: "faithful", False: "unfaithful"}
    confusion: dict[str, int] = {}
    for judge, human in pairs:
        key = f"judge {label[judge]} / human {label[human]}"
        confusion[key] = confusion.get(key, 0) + 1
    agreed = sum(1 for m in done if m.agree)
    return Agreement(
        marked=len(done),
        unmarked=[m.item_id for m in marks if m.agree is None],
        agreed=agreed,
        rate=agreed / len(done) if done else None,
        kappa=cohens_kappa(pairs),
        confusion=confusion,
    )
