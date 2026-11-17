from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from docqa.config import Settings
from docqa.db.models import Chunk, Document, DocumentStatus, Section
from tests.integration.helpers import create_workspace, run_worker, signup, upload_pdf

ALL_STAGES = {"parsing", "chunking", "embedding", "indexing"}


@pytest.fixture
async def workspace(client: AsyncClient) -> dict[str, Any]:
    await signup(client, "owner@example.org")
    return await create_workspace(client, "Reports")


async def test_upload_ingests_pdf_with_page_numbers(
    client: AsyncClient,
    workspace: dict[str, Any],
    settings: Settings,
    db_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    resp = await upload_pdf(client, workspace["id"])
    assert resp.status_code == 202, resp.text
    doc = resp.json()
    assert doc["status"] == "queued"
    assert doc["job"]["status"] == "queued"

    await run_worker(settings)

    status = (await client.get(f"/workspaces/{workspace['id']}/documents/{doc['id']}")).json()
    assert status["status"] == "ready"
    job = status["job"]
    assert (job["status"], job["stage"], job["progress"], job["attempts"]) == (
        "done",
        "done",
        100,
        1,
    )
    assert set(job["stage_seconds"]) == ALL_STAGES
    assert job["pages_per_minute"] > 0
    assert status["page_count"] == 3

    async with db_sessionmaker() as db:
        sections = (await db.execute(select(Section).order_by(Section.ordinal))).scalars().all()
        chunks = (await db.execute(select(Chunk).order_by(Chunk.ordinal))).scalars().all()
    assert [s.title for s in sections] == ["Page 1", "Page 2", "Page 3"]
    by_text = {c.text: c for c in chunks}
    portugal = next(c for t, c in by_text.items() if "Portugal" in t)
    assert (portugal.page_start, portugal.page_end) == (3, 3)
    table = next(c for c in chunks if c.is_table)
    assert table.page_start == 2
    assert "Total revenue | 2025: 20,700 | 2024: 18,950" in table.text
    assert all(c.embedding is not None and len(c.embedding) == 384 for c in chunks)
    assert {c.index_config for c in chunks} == {"section-512-64"}
    assert all(c.heading.startswith("sample_report — Page ") for c in chunks)


async def test_non_pdf_rejected(client: AsyncClient, workspace: dict[str, Any]) -> None:
    resp = await upload_pdf(client, workspace["id"], b"hello", "notes.txt", "text/plain")
    assert resp.status_code == 415
    # Right extension and MIME type, wrong magic bytes.
    resp = await upload_pdf(client, workspace["id"], b"MZ\x90\x00 not a pdf", "fake.pdf")
    assert resp.status_code == 415
    assert (await client.get(f"/workspaces/{workspace['id']}/documents")).json() == []


async def test_oversized_upload_rejected(
    client: AsyncClient, workspace: dict[str, Any], settings: Settings
) -> None:
    before = set(settings.upload_dir.rglob("*"))
    too_big = b"%PDF-1.4\n" + b"0" * settings.max_upload_bytes
    resp = await upload_pdf(client, workspace["id"], too_big)
    assert resp.status_code == 413
    assert {p for p in settings.upload_dir.rglob("*") if p.is_file()} <= before  # nothing kept


async def test_corrupt_pdf_fails_without_retries(
    client: AsyncClient, workspace: dict[str, Any], settings: Settings
) -> None:
    resp = await upload_pdf(client, workspace["id"], b"%PDF-1.4\nbroken", "broken.pdf")
    await run_worker(settings)
    status = (
        await client.get(f"/workspaces/{workspace['id']}/documents/{resp.json()['id']}")
    ).json()
    assert status["status"] == "failed"
    assert status["job"]["attempts"] == 1
    assert status["job"]["error"] == "The file could not be read as a PDF."


async def test_transient_failure_retried_then_marked_failed(
    client: AsyncClient,
    workspace: dict[str, Any],
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[int] = []

    async def boom(*args: Any, **kwargs: Any) -> None:
        calls.append(1)
        raise ConnectionError("database went away")

    monkeypatch.setattr("docqa.worker.tasks.run_ingestion", boom)
    resp = await upload_pdf(client, workspace["id"])
    await run_worker(settings)

    expected_attempts = 1 + settings.ingest_max_retries
    assert len(calls) == expected_attempts
    status = (
        await client.get(f"/workspaces/{workspace['id']}/documents/{resp.json()['id']}")
    ).json()
    assert status["status"] == "failed"
    assert status["job"]["status"] == "failed"
    assert status["job"]["attempts"] == expected_attempts
    assert f"Gave up after {expected_attempts} attempts" in status["job"]["error"]
    assert "database went away" not in status["job"]["error"]  # internals aren't leaked

    # A failed upload can be retried with a fresh job, which then succeeds.
    monkeypatch.undo()
    retry = await client.post(f"/workspaces/{workspace['id']}/documents/{resp.json()['id']}/retry")
    assert retry.status_code == 202
    await run_worker(settings)
    status = (
        await client.get(f"/workspaces/{workspace['id']}/documents/{resp.json()['id']}")
    ).json()
    assert status["status"] == "ready"


async def test_documents_are_private_to_their_workspace(
    client: AsyncClient, other_client: AsyncClient, workspace: dict[str, Any], settings: Settings
) -> None:
    doc = (await upload_pdf(client, workspace["id"])).json()
    await signup(other_client, "intruder@example.org")
    own = await create_workspace(other_client, "Mine")

    base = f"/workspaces/{workspace['id']}/documents"
    assert (await other_client.get(base)).status_code == 404
    assert (await other_client.get(f"{base}/{doc['id']}")).status_code == 404
    assert (await other_client.delete(f"{base}/{doc['id']}")).status_code == 404
    assert (await upload_pdf(other_client, workspace["id"])).status_code == 404
    # Guessing the document id under one's own workspace doesn't work either.
    assert (
        await other_client.get(f"/workspaces/{own['id']}/documents/{doc['id']}")
    ).status_code == 404


async def test_delete_removes_document_and_file(
    client: AsyncClient,
    workspace: dict[str, Any],
    settings: Settings,
    db_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    doc = (await upload_pdf(client, workspace["id"])).json()
    await run_worker(settings)
    async with db_sessionmaker() as db:
        path = (await db.get(Document, doc["id"])).storage_path  # type: ignore[union-attr]
    resp = await client.delete(f"/workspaces/{workspace['id']}/documents/{doc['id']}")
    assert resp.status_code == 204
    async with db_sessionmaker() as db:
        assert (await db.execute(select(Chunk))).scalars().all() == []
    assert not __import__("pathlib").Path(path).exists()


async def test_library_attach_and_detach(
    client: AsyncClient,
    other_client: AsyncClient,
    workspace: dict[str, Any],
    db_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    async with db_sessionmaker() as db:
        filing = Document(
            is_library=True, title="Acme 10-K FY2025", filename="acme.htm",
            source_type="html_10k", status=DocumentStatus.READY, storage_path="/dev/null",
            size_bytes=1, sha256="0" * 64, ticker="ACME", company_name="Acme",
            form_type="10-K", fiscal_year=2025, accession_number="0000000001-26-000001",
        )  # fmt: skip
        db.add(filing)
        await db.commit()
        filing_id = str(filing.id)

    assert [d["id"] for d in (await client.get("/library/documents")).json()] == [filing_id]
    base = f"/workspaces/{workspace['id']}"
    assert (await client.get(f"{base}/documents")).json() == []

    attached = await client.post(f"{base}/library", json={})
    assert attached.status_code == 200
    assert [d["id"] for d in attached.json()] == [filing_id]
    assert (await client.post(f"{base}/library", json={})).status_code == 200  # idempotent
    assert (await client.get(f"{base}/documents/{filing_id}")).json()["is_library"] is True
    # Library filings are shared: they can be detached, not deleted.
    assert (await client.delete(f"{base}/documents/{filing_id}")).status_code == 409

    # Another user's workspace doesn't see it until they attach it themselves.
    await signup(other_client, "second@example.org")
    other_ws = await create_workspace(other_client, "Theirs")
    assert (await other_client.get(f"/workspaces/{other_ws['id']}/documents")).json() == []

    assert (await client.delete(f"{base}/library/{filing_id}")).status_code == 204
    assert (await client.get(f"{base}/documents")).json() == []
    assert (await client.get("/library/documents")).json()[0]["id"] == filing_id
