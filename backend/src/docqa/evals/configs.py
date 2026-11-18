"""Eval configuration files (`evals/configs/*.yaml`) and stable hashes of them."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any

import yaml

from docqa.config import REPO_ROOT
from docqa.ingestion.chunking import ChunkingConfig
from docqa.retrieval.retriever import RetrievalConfig

CONFIG_DIR = REPO_ROOT / "evals" / "configs"
_RETRIEVAL_FIELDS = {f.name for f in fields(RetrievalConfig)}


def retrieval_config(values: dict[str, Any]) -> RetrievalConfig:
    unknown = set(values) - _RETRIEVAL_FIELDS
    if unknown:
        raise ValueError(f"unknown retrieval settings: {sorted(unknown)}")
    return RetrievalConfig(**values)


def stable_hash(value: Any) -> str:
    """Short hash of a JSON-serializable value (dataclasses allowed), independent of key order."""
    if hasattr(value, "__dataclass_fields__"):
        value = asdict(value)
    payload = json.dumps(value, sort_keys=True, default=str).encode()
    return hashlib.sha256(payload).hexdigest()[:12]


@dataclass(frozen=True)
class AblationPlan:
    indexes: list[ChunkingConfig]
    base: RetrievalConfig
    groups: dict[str, dict[str, RetrievalConfig]]


def load_ablations(path: Path = CONFIG_DIR / "ablations.yaml") -> AblationPlan:
    raw = yaml.safe_load(path.read_text())
    base_values = dict(raw["base"])
    groups = {
        group: {
            name: retrieval_config(base_values | (overrides or {}))
            for name, overrides in variants.items()
        }
        for group, variants in raw["groups"].items()
    }
    return AblationPlan(
        indexes=[ChunkingConfig(**i) for i in raw["indexes"]],
        base=retrieval_config(base_values),
        groups=groups,
    )


@dataclass(frozen=True)
class GenerationConfig:
    name: str
    retrieval: RetrievalConfig
    refusal_min_rerank_score: float

    @property
    def hash(self) -> str:
        return stable_hash(self)


def load_generation_config(path: Path = CONFIG_DIR / "final.yaml") -> GenerationConfig:
    raw = yaml.safe_load(path.read_text())
    return GenerationConfig(
        name=raw["name"],
        retrieval=retrieval_config(raw["retrieval"]),
        refusal_min_rerank_score=float(raw["refusal_min_rerank_score"]),
    )
