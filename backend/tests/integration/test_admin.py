from __future__ import annotations

import pytest
from sqlalchemy import make_url, text
from sqlalchemy.ext.asyncio import create_async_engine

from docqa.config import Settings
from docqa.db.admin import recreate_database


async def test_recreate_database_drops_existing_contents(settings: Settings) -> None:
    url = make_url(settings.database_url).set(database="docqa_admin_check")
    await recreate_database(url.render_as_string(hide_password=False))
    engine = create_async_engine(url)
    try:
        async with engine.begin() as conn:
            await conn.execute(text("CREATE TABLE leftover (id int)"))
        # An open connection must not block the drop (FORCE terminates it).
        held = await engine.connect()
        await held.execute(text("SELECT 1"))
        await recreate_database(url.render_as_string(hide_password=False))
        await held.invalidate()
        await engine.dispose()
        async with engine.connect() as conn:
            exists = await conn.scalar(text("SELECT to_regclass('leftover') IS NOT NULL"))
        assert exists is False
    finally:
        await engine.dispose()
        admin = create_async_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
        async with admin.connect() as conn:
            await conn.execute(text('DROP DATABASE IF EXISTS "docqa_admin_check" WITH (FORCE)'))
        await admin.dispose()


async def test_recreate_database_refuses_maintenance_db(settings: Settings) -> None:
    url = make_url(settings.database_url).set(database="postgres")
    with pytest.raises(ValueError, match="Refusing"):
        await recreate_database(url.render_as_string(hide_password=False))
