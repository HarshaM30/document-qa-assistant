"""pgvector cosine search over chunk embeddings (HNSW index)."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from docqa.db.models import Chunk


async def vector_search(
    db: AsyncSession,
    query_embedding: Sequence[float],
    scope: Any,
    k: int,
    ef_search: int,
) -> list[tuple[uuid.UUID, float]]:
    """Top-k (chunk id, cosine distance), nearest first.

    The workspace filter is applied during the index scan; iterative scanning keeps
    pulling candidates until k rows pass it, so small workspaces still get k results.
    """
    # Transaction-local, so the settings never leak to other users of the pooled connection.
    await db.execute(
        text(
            "SELECT set_config('hnsw.ef_search', :ef, true), "
            "set_config('hnsw.iterative_scan', 'relaxed_order', true)"
        ),
        {"ef": str(max(ef_search, k))},
    )
    distance = Chunk.embedding.cosine_distance(list(query_embedding))
    rows = await db.execute(
        select(Chunk.id, distance.label("distance"))
        .where(scope, Chunk.embedding.is_not(None))
        .order_by(distance)
        .limit(k)
    )
    # relaxed_order can return slightly out-of-order rows; restore exact order.
    return sorted(((r.id, float(r.distance)) for r in rows), key=lambda r: r[1])
