from __future__ import annotations

import math
from typing import Dict, List

from app.models import CandidatePaper, SearchResultItem, SubScores, Weights


def _relevance_scores(candidates: List[CandidatePaper]) -> Dict[str, float]:
    n = len(candidates)
    if n <= 1:
        return {c.arxiv_id: 1.0 for c in candidates}
    return {c.arxiv_id: (n - 1 - c.relevance_rank) / (n - 1) for c in candidates}


def _citation_scores(
    candidates: List[CandidatePaper], citation_counts: Dict[str, int]
) -> Dict[str, float]:
    logs = {c.arxiv_id: math.log1p(citation_counts.get(c.arxiv_id, 0)) for c in candidates}
    max_log = max(logs.values()) if logs else 0.0
    if max_log == 0.0:
        return {aid: 0.0 for aid in logs}
    return {aid: value / max_log for aid, value in logs.items()}


def _recency_scores(candidates: List[CandidatePaper]) -> Dict[str, float]:
    ordinals = {c.arxiv_id: c.published.toordinal() for c in candidates}
    lo, hi = min(ordinals.values()), max(ordinals.values())
    if hi == lo:
        return {aid: 1.0 for aid in ordinals}
    return {aid: (value - lo) / (hi - lo) for aid, value in ordinals.items()}


def rank(
    candidates: List[CandidatePaper],
    citation_counts: Dict[str, int],
    weights: Weights,
    n: int,
) -> List[SearchResultItem]:
    if not candidates:
        return []
    rel = _relevance_scores(candidates)
    cit = _citation_scores(candidates, citation_counts)
    rec = _recency_scores(candidates)

    items: List[SearchResultItem] = []
    for c in candidates:
        sub = SubScores(
            relevance=rel[c.arxiv_id],
            citations=cit[c.arxiv_id],
            recency=rec[c.arxiv_id],
        )
        final = (
            weights.relevance * sub.relevance
            + weights.citations * sub.citations
            + weights.recency * sub.recency
        )
        items.append(
            SearchResultItem(
                arxiv_id=c.arxiv_id,
                title=c.title,
                authors=c.authors,
                abstract=c.abstract,
                published=c.published,
                url=c.url,
                citation_count=citation_counts.get(c.arxiv_id, 0),
                sub_scores=sub,
                final_score=final,
                citation_data_missing=c.arxiv_id not in citation_counts,
            )
        )

    items.sort(key=lambda it: it.final_score, reverse=True)
    return items[:n]
