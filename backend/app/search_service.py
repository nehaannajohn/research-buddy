from __future__ import annotations

import uuid
from typing import Dict, List

from app.arxiv_client import ArxivUnavailable
from app.citation_client import CitationUnavailable
from app.models import SearchRequest, SearchResponse, SearchResultItem, SortKey
from app.sorter import build_result_items, sort_papers
from app.store import ResultStore

POOL_SIZE = 200


class SearchSourceUnavailable(Exception):
    """Raised when the primary source (arXiv) is unavailable."""


class SearchNotFound(Exception):
    """Raised when a search_id is not present in the store (unknown or expired)."""


class SearchService:
    def __init__(self, arxiv_client, citation_client, store: ResultStore) -> None:
        self.arxiv_client = arxiv_client
        self.citation_client = citation_client
        self.store = store

    def search(self, request: SearchRequest) -> SearchResponse:
        try:
            candidates = self.arxiv_client.search(request.query, POOL_SIZE)
        except ArxivUnavailable as exc:
            raise SearchSourceUnavailable(str(exc))

        warnings: List[str] = []

        if not candidates:
            warnings.append("No matches found. Try broadening your query.")
            return self._store_and_respond([], warnings, request.n)

        try:
            citation_counts: Dict[str, int] = self.citation_client.get_citation_counts(
                [c.arxiv_id for c in candidates]
            )
        except CitationUnavailable:
            citation_counts = {}
            warnings.append(
                "Citation data unavailable — sorting by citations may be incomplete."
            )

        items = build_result_items(candidates, citation_counts)
        return self._store_and_respond(items, warnings, request.n)

    def resort(self, search_id: str, sort_key: SortKey, n: int) -> List[SearchResultItem]:
        items = self.store.get(search_id)
        if items is None:
            raise SearchNotFound(search_id)
        return sort_papers(items, sort_key, n)

    def _store_and_respond(
        self, items: List[SearchResultItem], warnings: List[str], n: int
    ) -> SearchResponse:
        search_id = uuid.uuid4().hex
        self.store.save(search_id, items)
        results = sort_papers(items, SortKey.relevance, n)
        return SearchResponse(
            search_id=search_id,
            results=results,
            pool_size=len(items),
            warnings=warnings,
        )
