"""Faithfulness judge: is every claim in the answer supported by the passages it was given?

The judge must be a different model from the one that wrote the answer (a model grading
its own output tends to favour it); `assert_distinct_models` enforces that at startup.
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from docqa.generation.llm import LLMSpec

JUDGE_SYSTEM = """You check answers produced by a retrieval-augmented assistant for \
faithfulness to its source passages.

An answer is FAITHFUL if every factual claim in it (numbers, dates, names, comparisons, \
directions of change) is stated in or directly follows from the numbered passages. \
Simple arithmetic on numbers in the passages (differences, ratios, rounding) is allowed. \
Citation markers like [2] refer to the passages; a claim cited to the wrong passage but \
supported by another passage is still faithful. Ignore style and completeness: judge only \
whether what the answer says is supported.

An answer is UNFAITHFUL if any claim is missing from, or contradicts, the passages.

Reply with only a JSON object, no other text:
{"verdict": "faithful" | "unfaithful", "unsupported_claims": ["..."], "reason": "one sentence"}"""

JUDGE_USER = "Passages:\n\n{passages}\n\nQuestion: {question}\n\nAnswer to check:\n{answer}"


class SameModelError(ValueError):
    pass


def assert_distinct_models(answer: LLMSpec, judge: LLMSpec) -> None:
    if answer.litellm_model.lower() == judge.litellm_model.lower():
        raise SameModelError(
            f"The judge model must differ from the answer model (both are "
            f"{answer.litellm_model}). Set JUDGE_MODEL to a different model."
        )


def judge_messages(passages: str, question: str, answer: str) -> list[dict[str, Any]]:
    return [
        {"role": "system", "content": JUDGE_SYSTEM},
        {
            "role": "user",
            "content": JUDGE_USER.format(passages=passages, question=question, answer=answer),
        },
    ]


@dataclass(frozen=True)
class Verdict:
    faithful: bool | None  # None when the judge's reply couldn't be parsed
    reason: str = ""
    unsupported_claims: Sequence[str] = field(default_factory=tuple)
    raw: str = ""

    @property
    def label(self) -> str:
        return {True: "faithful", False: "unfaithful", None: "unparsed"}[self.faithful]

    def to_json(self) -> dict[str, Any]:
        return {
            "verdict": self.label,
            "reason": self.reason,
            "unsupported_claims": list(self.unsupported_claims),
            "raw": self.raw,
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> Verdict:
        faithful = {"faithful": True, "unfaithful": False}.get(data.get("verdict", ""))
        return cls(
            faithful,
            data.get("reason", ""),
            tuple(data.get("unsupported_claims", [])),
            data.get("raw", ""),
        )


_THINK = re.compile(r"<think>.*?</think>", re.S | re.I)
_OBJECT = re.compile(r"\{.*\}", re.S)


def parse_verdict(text: str) -> Verdict:
    """Read the judge's JSON, tolerating reasoning blocks and code fences around it."""
    body = _THINK.sub("", text)
    match = _OBJECT.search(body)
    if match:
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            data = None
        if isinstance(data, dict):
            verdict = str(data.get("verdict", "")).strip().lower()
            if verdict in ("faithful", "unfaithful"):
                claims = data.get("unsupported_claims") or []
                return Verdict(
                    verdict == "faithful",
                    str(data.get("reason", "")),
                    tuple(str(c) for c in claims) if isinstance(claims, list) else (),
                    text,
                )
    lowered = body.lower()
    if "unfaithful" in lowered:
        return Verdict(False, "verdict read from free text", (), text)
    return Verdict(None, "could not parse judge reply", (), text)
