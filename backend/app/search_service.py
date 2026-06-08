from __future__ import annotations

import uuid
from typing import Dict, List

from app.arxiv_client import ArxivUnavailable
from app.citation_client import CitationUnavailable
from app.models import SearchRequest, SearchResponse, Weights
from app.ranker import rank
from app.store import ResultStore


class SearchSourceUnavailable(Exception):
    """Raised when the primary source (arXiv) is unavailable."""


class SearchService:
    def __init__(self, arxiv_client, citation_client, store: ResultStore) -> None:
        self.arxiv_client = arxiv_client
        self.citation_client = citation_client
        self.store = store

    def search(self, request: SearchRequest) -> SearchResponse:
        weights = request.weights or Weights()
        pool_size = max(50, request.n * 5)

        try:
            candidates = self.arxiv_client.search(request.query, pool_size)
        except ArxivUnavailable as exc:
            raise SearchSourceUnavailable(str(exc))

        warnings: List[str] = []

        if not candidates:
            return self._store_and_respond(
                results=[],
                pool_size=pool_size,
                warnings=["No matches found. Try broadening your query."],
            )

        try:
            citation_counts: Dict[str, int] = self.citation_client.get_citation_counts(
                [c.arxiv_id for c in candidates]
            )
        except CitationUnavailable:
            citation_counts = {}
            warnings.append(
                "Citation data unavailable; ranked on relevance and recency only."
            )

        results = rank(candidates, citation_counts, weights, request.n)
        return self._store_and_respond(results, pool_size, warnings)

    def _store_and_respond(self, results, pool_size, warnings) -> SearchResponse:
        search_id = uuid.uuid4().hex
        self.store.save(search_id, results)
        return SearchResponse(
            search_id=search_id,
            results=results,
            pool_size=pool_size,
            warnings=warnings,
        )
