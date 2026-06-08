from __future__ import annotations

from typing import List

from app.models import SearchResultItem, SortKey


def sort_papers(
    items: List[SearchResultItem], sort_key: SortKey, n: int
) -> List[SearchResultItem]:
    """Return the top ``n`` items sorted by ``sort_key``.

    ``relevance`` keeps the input (OpenAlex relevance) order. ``citations`` and
    ``recency`` use a stable descending sort, so ties preserve the input order.
    """
    if sort_key == SortKey.citations:
        ordered = sorted(items, key=lambda it: it.citation_count, reverse=True)
    elif sort_key == SortKey.recency:
        ordered = sorted(items, key=lambda it: it.published, reverse=True)
    else:  # SortKey.relevance — input is already in relevance order
        ordered = list(items)
    return ordered[:n]
