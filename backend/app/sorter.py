from __future__ import annotations

from typing import Dict, List

from app.models import CandidatePaper, SearchResultItem, SortKey


def build_result_items(
    candidates: List[CandidatePaper], citation_counts: Dict[str, int]
) -> List[SearchResultItem]:
    """Combine arXiv candidates with citation counts, preserving arXiv (relevance) order.

    IDs absent from ``citation_counts`` get count 0 and are flagged as missing.
    """
    items: List[SearchResultItem] = []
    for c in candidates:
        items.append(
            SearchResultItem(
                arxiv_id=c.arxiv_id,
                title=c.title,
                authors=c.authors,
                abstract=c.abstract,
                published=c.published,
                url=c.url,
                citation_count=citation_counts.get(c.arxiv_id, 0),
                citation_data_missing=c.arxiv_id not in citation_counts,
            )
        )
    return items


def sort_papers(
    items: List[SearchResultItem], sort_key: SortKey, n: int
) -> List[SearchResultItem]:
    """Return the top ``n`` items sorted by ``sort_key``.

    ``relevance`` keeps the input (arXiv) order. ``citations`` and ``recency`` use a
    stable descending sort, so ties preserve the underlying relevance order.
    """
    if sort_key == SortKey.citations:
        ordered = sorted(items, key=lambda it: it.citation_count, reverse=True)
    elif sort_key == SortKey.recency:
        ordered = sorted(items, key=lambda it: it.published, reverse=True)
    else:  # SortKey.relevance — input is already in arXiv order
        ordered = list(items)
    return ordered[:n]
