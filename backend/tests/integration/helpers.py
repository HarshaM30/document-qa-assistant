from __future__ import annotations

from typing import Any

from httpx import ASGITransport, AsyncClient

from docqa.auth.deps import CSRF_HEADER

PASSWORD = "correct-horse-battery"


def make_client(app: Any) -> AsyncClient:
    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        headers={CSRF_HEADER: "XMLHttpRequest"},
    )


async def signup(client: AsyncClient, email: str, password: str = PASSWORD) -> dict[str, Any]:
    resp = await client.post("/auth/signup", json={"email": email, "password": password})
    assert resp.status_code == 201, resp.text
    body: dict[str, Any] = resp.json()
    return body


async def create_workspace(client: AsyncClient, name: str = "Research") -> dict[str, Any]:
    resp = await client.post("/workspaces", json={"name": name})
    assert resp.status_code == 201, resp.text
    body: dict[str, Any] = resp.json()
    return body


FIXTURES = __import__("pathlib").Path(__file__).parents[1] / "fixtures"
SAMPLE_PDF = FIXTURES / "sample_report.pdf"


async def upload_pdf(
    client: AsyncClient,
    workspace_id: str,
    content: bytes | None = None,
    filename: str = "sample_report.pdf",
    content_type: str = "application/pdf",
) -> Any:
    data = SAMPLE_PDF.read_bytes() if content is None else content
    return await client.post(
        f"/workspaces/{workspace_id}/documents",
        files={"file": (filename, data, content_type)},
    )


async def run_worker(settings: Any) -> None:
    """Drain the arq queue in-process (burst mode), including any retries."""
    from arq.connections import RedisSettings
    from arq.worker import Worker

    from docqa.worker.settings import worker_functions
    from docqa.worker.tasks import shutdown, startup

    worker = Worker(
        functions=worker_functions(settings),
        redis_settings=RedisSettings.from_dsn(settings.redis_url),
        burst=True,
        poll_delay=0.05,
        max_jobs=1,
        handle_signals=False,
        on_startup=startup,
        on_shutdown=shutdown,
        ctx={"settings": settings},
    )
    try:
        await worker.main()
    finally:
        await worker.close()
