"""Reciprocal rank fusion."""

from __future__ import annotations

from collections.abc import Hashable, Sequence


def reciprocal_rank_fusion[K: Hashable](
    rankings: Sequence[Sequence[K]], k: int = 60
) -> list[tuple[K, float]]:
    """Fuse ranked lists: score(d) = sum over lists of 1 / (k + rank), ranks starting at 1.

    Ties keep the order in which items were first seen (earlier lists, better ranks first),
    so the output is deterministic.
    """
    if k < 0:
        raise ValueError("k must be non-negative")
    scores: dict[K, float] = {}
    for ranking in rankings:
        for rank, item in enumerate(ranking, start=1):
            scores[item] = scores.get(item, 0.0) + 1.0 / (k + rank)
    first_seen = {item: i for i, item in enumerate(scores)}
    return sorted(scores.items(), key=lambda kv: (-kv[1], first_seen[kv[0]]))
