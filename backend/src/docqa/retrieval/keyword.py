"""Postgres full-text search over the generated `chunks.tsv` column (GIN index)."""

from __future__ import annotations

import re
import uuid
from typing import Any

from sqlalchemy import func, literal_column, select
from sqlalchemy.ext.asyncio import AsyncSession

from docqa.db.models import Chunk

_TERM = re.compile(r"[A-Za-z0-9]+")
_OPERATORS = frozenset({"or", "and", "not"})
# ts_rank_cd normalization 1: divide by 1 + log(document length), so long chunks don't win
# on length alone.
_RANK_NORMALIZATION = 1


def or_query(question: str) -> str:
    """Turn a question into a websearch query that matches ANY of its terms.

    `websearch_to_tsquery` ANDs bare words, and a natural-language question almost never
    has every word in one passage. Joining terms with `or` lets ranking do the work.
    Stop words are dropped by the English parser.
    """
    terms = [t for t in _TERM.findall(question) if t.lower() not in _OPERATORS]
    return " or ".join(terms)


async def keyword_search(
    db: AsyncSession, question: str, scope: Any, k: int
) -> list[tuple[uuid.UUID, float]]:
    """Top-k (chunk id, ts_rank_cd score), best first."""
    q = or_query(question)
    if not q:
        return []
    tsquery = func.websearch_to_tsquery(literal_column("'english'"), q)
    rank = func.ts_rank_cd(Chunk.tsv, tsquery, _RANK_NORMALIZATION)
    rows = await db.execute(
        select(Chunk.id, rank.label("rank"))
        .where(scope, Chunk.tsv.bool_op("@@")(tsquery))
        .order_by(rank.desc(), Chunk.id)
        .limit(k)
    )
    return [(r.id, float(r.rank)) for r in rows]
