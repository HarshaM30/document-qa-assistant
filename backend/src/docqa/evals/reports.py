"""Timestamped markdown + JSON reports in `evals/reports/`, each tagged with the dataset version."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from docqa.config import REPO_ROOT
from docqa.evals.dataset import Dataset

REPORT_DIR = REPO_ROOT / "evals" / "reports"


def timestamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def write_report(
    kind: str,
    dataset: Dataset,
    data: dict[str, Any],
    markdown: str,
    *,
    out_dir: Path = REPORT_DIR,
) -> tuple[Path, Path]:
    """Write `<timestamp>-<kind>.md` and `.json`; returns both paths."""
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = timestamp()
    meta = {"kind": kind, "created_at": stamp, "dataset": dataset.version}
    json_path = out_dir / f"{stamp}-{kind}.json"
    md_path = out_dir / f"{stamp}-{kind}.md"
    json_path.write_text(json.dumps(meta | data, indent=2, default=str) + "\n")
    header = f"_Dataset: `{dataset.version}` · generated {stamp}_\n\n"
    md_path.write_text(
        markdown.replace("\n", "\n" + header, 1) if markdown.startswith("# ") else header + markdown
    )
    return md_path, json_path


def table(headers: list[str], rows: list[list[Any]]) -> str:
    """A GitHub-flavoured markdown table."""
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    lines += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return "\n".join(lines)


def pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.1%}"
