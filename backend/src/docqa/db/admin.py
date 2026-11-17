"""Database administration helpers (dropping and recreating a throwaway database)."""

from __future__ import annotations

from sqlalchemy import make_url, text
from sqlalchemy.ext.asyncio import create_async_engine


async def recreate_database(url: str) -> None:
    """Drop the database named in `url` (disconnecting any clients) and create it empty."""
    target = make_url(url)
    name = target.database
    if not name or name == "postgres":
        raise ValueError(f"Refusing to recreate database {name!r}")
    admin = create_async_engine(target.set(database="postgres"), isolation_level="AUTOCOMMIT")
    quoted = '"' + name.replace('"', '""') + '"'
    try:
        async with admin.connect() as conn:
            await conn.execute(text(f"DROP DATABASE IF EXISTS {quoted} WITH (FORCE)"))
            await conn.execute(text(f"CREATE DATABASE {quoted}"))
    finally:
        await admin.dispose()
