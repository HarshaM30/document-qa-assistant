"""Startup check that the embedding and reranker ONNX files are already downloaded.

Models load lazily, so a missing file would otherwise surface as a slow (or failing)
download on the first question or the first upload. The check only looks at the cache on
disk; it never loads a model.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from docqa.config import Settings

log = logging.getLogger(__name__)


class ModelFilesMissingError(RuntimeError):
    pass


@dataclass(frozen=True)
class ModelFile:
    model: str
    kind: str  # "embedding" | "reranker"
    path: Path | None  # the ONNX file, if found

    @property
    def present(self) -> bool:
        return self.path is not None


def _description(kind: str, model: str) -> dict[str, object] | None:
    if kind == "embedding":
        from fastembed import TextEmbedding

        supported = TextEmbedding.list_supported_models()
    else:
        from fastembed.rerank.cross_encoder import TextCrossEncoder

        supported = TextCrossEncoder.list_supported_models()
    return next((m for m in supported if m["model"] == model), None)


def locate(cache_dir: Path, kind: str, model: str) -> ModelFile:
    """Find the model's ONNX file in fastembed's Hugging Face-style cache."""
    desc = _description(kind, model)
    if desc is None:
        return ModelFile(model, kind, None)
    sources = desc.get("sources") or {}
    repo = sources.get("hf") if isinstance(sources, dict) else None
    model_file = str(desc.get("model_file") or "")
    if not repo or not model_file:
        return ModelFile(model, kind, None)
    snapshots = cache_dir / f"models--{str(repo).replace('/', '--')}" / "snapshots"
    for snapshot in sorted(snapshots.glob("*")) if snapshots.is_dir() else []:
        candidate = snapshot / model_file
        if candidate.is_file() and candidate.stat().st_size > 0:
            return ModelFile(model, kind, candidate)
    return ModelFile(model, kind, None)


def check_model_files(settings: Settings, *, need_reranker: bool = True) -> list[ModelFile]:
    files = [locate(settings.fastembed_cache_dir, "embedding", settings.embedding_model)]
    if need_reranker:
        files.append(locate(settings.fastembed_cache_dir, "reranker", settings.reranker_model))
    return files


def enforce_model_files(settings: Settings, *, need_reranker: bool = True) -> list[ModelFile]:
    """Apply MODEL_FILES_CHECK: `off` skips, `warn` logs, `require` raises."""
    if settings.model_files_check == "off":
        return []
    files = check_model_files(settings, need_reranker=need_reranker)
    missing = [f for f in files if not f.present]
    if missing:
        names = ", ".join(f"{f.kind} model {f.model}" for f in missing)
        message = (
            f"Model files not found in {settings.fastembed_cache_dir}: {names}. "
            "Run `docqa download-models` (or `make models`) first."
        )
        if settings.model_files_check == "require":
            raise ModelFilesMissingError(message)
        log.warning("%s They will be downloaded on first use.", message)
    return files
