"""Local-disk storage for uploaded files."""

from __future__ import annotations

import hashlib
import re
import unicodedata
import uuid
from dataclasses import dataclass
from pathlib import Path

from fastapi import UploadFile

PDF_MAGIC = b"%PDF-"
_READ_CHUNK = 1 << 20


class UploadTooLargeError(Exception):
    pass


class NotAPdfError(Exception):
    pass


@dataclass
class StoredFile:
    path: Path
    size_bytes: int
    sha256: str


def safe_display_name(filename: str | None, fallback: str = "document.pdf") -> str:
    """Strip directories, control characters and odd whitespace from a client filename."""
    name = (filename or "").replace("\\", "/").rsplit("/", 1)[-1]
    name = unicodedata.normalize("NFKC", name)
    name = "".join(ch for ch in name if unicodedata.category(ch)[0] != "C")
    name = re.sub(r"\s+", " ", name).strip(" .")
    return name[:200] or fallback


def upload_path(upload_dir: Path, workspace_id: uuid.UUID, document_id: uuid.UUID) -> Path:
    # The on-disk name never comes from the client.
    return upload_dir / str(workspace_id) / f"{document_id}.pdf"


async def save_pdf_upload(upload: UploadFile, dest: Path, max_bytes: int) -> StoredFile:
    """Stream an upload to `dest`, enforcing the size limit and the PDF magic bytes."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".part")
    digest = hashlib.sha256()
    size = 0
    try:
        with tmp.open("wb") as fh:
            first = True
            while chunk := await upload.read(_READ_CHUNK):
                if first:
                    if not chunk.startswith(PDF_MAGIC):
                        raise NotAPdfError
                    first = False
                size += len(chunk)
                if size > max_bytes:
                    raise UploadTooLargeError
                digest.update(chunk)
                fh.write(chunk)
        if size == 0:
            raise NotAPdfError
        tmp.replace(dest)
    finally:
        tmp.unlink(missing_ok=True)
    return StoredFile(path=dest, size_bytes=size, sha256=digest.hexdigest())
