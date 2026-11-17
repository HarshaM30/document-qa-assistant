"""Uploads, document status, and the shared SEC filings library."""

from __future__ import annotations

import asyncio
import logging
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, Request, UploadFile, status
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import distinct_on
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from docqa.api.workspaces import get_owned_workspace
from docqa.auth.deps import CurrentUser, DbDep, SettingsDep
from docqa.db.models import (
    Chunk,
    Document,
    DocumentStatus,
    IngestionJob,
    JobStatus,
    Section,
    SourceType,
    WorkspaceLibraryDocument,
)
from docqa.ingestion.pipeline import document_label
from docqa.retrieval.scope import document_visible_to
from docqa.schemas.chat import PassageOut
from docqa.schemas.documents import DocumentOut, JobOut, LibraryAttach
from docqa.storage import (
    NotAPdfError,
    UploadTooLargeError,
    safe_display_name,
    save_pdf_upload,
    upload_path,
)
from docqa.worker.tasks import INGEST_TASK

log = logging.getLogger(__name__)

router = APIRouter(tags=["documents"])

PDF_CONTENT_TYPES = {"application/pdf", "application/x-pdf"}


async def _latest_jobs(db: AsyncSession, doc_ids: list[uuid.UUID]) -> dict[uuid.UUID, IngestionJob]:
    if not doc_ids:
        return {}
    rows = await db.execute(
        select(IngestionJob)
        .where(IngestionJob.document_id.in_(doc_ids))
        .order_by(IngestionJob.document_id, IngestionJob.created_at.desc())
        .ext(distinct_on(IngestionJob.document_id))
    )
    return {job.document_id: job for job in rows.scalars()}


def _out(doc: Document, job: IngestionJob | None) -> DocumentOut:
    out = DocumentOut.model_validate(doc)
    out.job = JobOut.model_validate(job) if job else None
    return out


async def _get_visible_document(
    db: AsyncSession, workspace_id: uuid.UUID, document_id: uuid.UUID
) -> Document:
    doc = (
        await db.execute(
            select(Document).where(Document.id == document_id, document_visible_to(workspace_id))
        )
    ).scalar_one_or_none()
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Document not found")
    return doc


async def enqueue_ingestion(request: Request, job: IngestionJob) -> None:
    await request.app.state.arq.enqueue_job(
        INGEST_TASK, str(job.id), _job_id=f"ingest:{job.id}:{job.attempts}"
    )


@router.post(
    "/workspaces/{workspace_id}/documents",
    status_code=status.HTTP_202_ACCEPTED,
    responses={413: {"description": "File too large"}, 415: {"description": "Not a PDF"}},
)
async def upload_document(
    workspace_id: uuid.UUID,
    request: Request,
    user: CurrentUser,
    db: DbDep,
    settings: SettingsDep,
    file: Annotated[UploadFile, File(description="A PDF file")],
) -> DocumentOut:
    await get_owned_workspace(db, user, workspace_id)
    name = safe_display_name(file.filename)
    content_type = (file.content_type or "").split(";")[0].strip().lower()
    if content_type not in PDF_CONTENT_TYPES or not name.lower().endswith(".pdf"):
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Only PDF files are accepted"
        )

    document_id = uuid.uuid4()
    dest = upload_path(settings.upload_dir, workspace_id, document_id)
    try:
        stored = await save_pdf_upload(file, dest, settings.max_upload_bytes)
    except UploadTooLargeError:
        raise HTTPException(
            status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"File exceeds the {settings.max_upload_mb} MB limit",
        ) from None
    except NotAPdfError:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="File content is not a PDF"
        ) from None

    doc = Document(
        id=document_id,
        workspace_id=workspace_id,
        is_library=False,
        title=name.removesuffix(".pdf").removesuffix(".PDF") or name,
        filename=name,
        source_type=SourceType.PDF,
        status=DocumentStatus.QUEUED,
        storage_path=str(stored.path),
        size_bytes=stored.size_bytes,
        sha256=stored.sha256,
    )
    job = IngestionJob(document_id=document_id, max_attempts=1 + settings.ingest_max_retries)
    db.add_all([doc, job])
    await db.commit()
    try:
        await enqueue_ingestion(request, job)
    except Exception:
        log.exception("could not enqueue ingestion for %s", document_id)
        job.status, job.error = JobStatus.FAILED, "Could not queue the document for processing."
        doc.status = DocumentStatus.FAILED
        await db.commit()
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=job.error) from None
    return _out(doc, job)


@router.get("/workspaces/{workspace_id}/documents")
async def list_documents(
    workspace_id: uuid.UUID, user: CurrentUser, db: DbDep
) -> list[DocumentOut]:
    await get_owned_workspace(db, user, workspace_id)
    docs = list(
        (
            await db.execute(
                select(Document)
                .where(document_visible_to(workspace_id))
                .order_by(Document.is_library, Document.created_at)
            )
        ).scalars()
    )
    jobs = await _latest_jobs(db, [d.id for d in docs])
    return [_out(d, jobs.get(d.id)) for d in docs]


@router.get("/workspaces/{workspace_id}/documents/{document_id}")
async def get_document(
    workspace_id: uuid.UUID, document_id: uuid.UUID, user: CurrentUser, db: DbDep
) -> DocumentOut:
    """Document plus its latest ingestion job (stage, progress, error); polled by the UI."""
    await get_owned_workspace(db, user, workspace_id)
    doc = await _get_visible_document(db, workspace_id, document_id)
    jobs = await _latest_jobs(db, [doc.id])
    return _out(doc, jobs.get(doc.id))


@router.post(
    "/workspaces/{workspace_id}/documents/{document_id}/retry",
    status_code=status.HTTP_202_ACCEPTED,
)
async def retry_document(
    workspace_id: uuid.UUID,
    document_id: uuid.UUID,
    request: Request,
    user: CurrentUser,
    db: DbDep,
    settings: SettingsDep,
) -> DocumentOut:
    """Start a fresh ingestion job for a failed upload."""
    await get_owned_workspace(db, user, workspace_id)
    doc = await _get_visible_document(db, workspace_id, document_id)
    if doc.is_library or doc.status != DocumentStatus.FAILED:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Only failed uploads can be retried")
    job = IngestionJob(document_id=doc.id, max_attempts=1 + settings.ingest_max_retries)
    doc.status = DocumentStatus.QUEUED
    db.add(job)
    await db.commit()
    await enqueue_ingestion(request, job)
    return _out(doc, job)


@router.delete(
    "/workspaces/{workspace_id}/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_document(
    workspace_id: uuid.UUID, document_id: uuid.UUID, user: CurrentUser, db: DbDep
) -> None:
    await get_owned_workspace(db, user, workspace_id)
    doc = await _get_visible_document(db, workspace_id, document_id)
    if doc.is_library:
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="Library filings are shared; detach them instead"
        )
    path = doc.storage_path
    await db.delete(doc)
    await db.commit()
    await asyncio.to_thread(Path(path).unlink, missing_ok=True)


@router.get("/workspaces/{workspace_id}/passages/{chunk_id}")
async def get_passage(
    workspace_id: uuid.UUID, chunk_id: uuid.UUID, user: CurrentUser, db: DbDep
) -> PassageOut:
    """The full text and location of a cited chunk, if the workspace can see its document."""
    await get_owned_workspace(db, user, workspace_id)
    row = (
        await db.execute(
            select(Chunk, Section, Document)
            .join(Document, Document.id == Chunk.document_id)
            .outerjoin(Section, Section.id == Chunk.section_id)
            .where(Chunk.id == chunk_id, document_visible_to(workspace_id))
        )
    ).one_or_none()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Passage not found")
    chunk, section, doc = row
    return PassageOut(
        chunk_id=chunk.id,
        document_id=doc.id,
        document_title=document_label(doc),
        section_title=section.title if section else "",
        item_code=section.item_code if section else None,
        page_start=chunk.page_start,
        page_end=chunk.page_end,
        is_table=chunk.is_table,
        text=chunk.text,
    )


# --- Shared filings library ----------------------------------------------------------------


@router.get("/library/documents")
async def list_library(user: CurrentUser, db: DbDep) -> list[DocumentOut]:
    docs = (
        await db.execute(
            select(Document)
            .where(Document.is_library, Document.status == DocumentStatus.READY)
            .order_by(Document.ticker, Document.fiscal_year.desc())
        )
    ).scalars()
    return [_out(d, None) for d in docs]


@router.post("/workspaces/{workspace_id}/library", status_code=status.HTTP_200_OK)
async def attach_library(
    workspace_id: uuid.UUID, body: LibraryAttach, user: CurrentUser, db: DbDep
) -> list[DocumentOut]:
    """Attach library filings (all ready ones by default) to a workspace. Idempotent."""
    await get_owned_workspace(db, user, workspace_id)
    query = select(Document.id).where(Document.is_library, Document.status == DocumentStatus.READY)
    if body.document_ids is not None:
        query = query.where(Document.id.in_(body.document_ids))
    ids = list((await db.execute(query)).scalars())
    if body.document_ids is not None and len(ids) != len(set(body.document_ids)):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Library document not found")
    if ids:
        await db.execute(
            pg_insert(WorkspaceLibraryDocument)
            .values([{"workspace_id": workspace_id, "document_id": i} for i in ids])
            .on_conflict_do_nothing()
        )
        await db.commit()
    return await list_documents(workspace_id, user, db)


@router.delete(
    "/workspaces/{workspace_id}/library/{document_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def detach_library(
    workspace_id: uuid.UUID, document_id: uuid.UUID, user: CurrentUser, db: DbDep
) -> None:
    await get_owned_workspace(db, user, workspace_id)
    await db.execute(
        delete(WorkspaceLibraryDocument).where(
            WorkspaceLibraryDocument.workspace_id == workspace_id,
            WorkspaceLibraryDocument.document_id == document_id,
        )
    )
    await db.commit()
