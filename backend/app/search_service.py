from __future__ import annotations

import uuid
from typing import List

from app.models import SearchRequest, SearchResponse, SearchResultItem, SortKey
from app.openalex_client import OpenAlexUnavailable
from app.sorter import sort_papers
from app.store import ResultStore

POOL_SIZE = 200


class SearchSourceUnavailable(Exception):
    """Raised when the source (OpenAlex) is unavailable."""


class SearchNotFound(Exception):
    """Raised when a search_id is not present in the store (unknown or expired)."""


class SearchService:
    def __init__(self, openalex_client, store: ResultStore) -> None:
        self.openalex_client = openalex_client
        self.store = store

    def search(self, request: SearchRequest) -> SearchResponse:
        try:
            items = self.openalex_client.search(request.query, POOL_SIZE)
        except OpenAlexUnavailable as exc:
            raise SearchSourceUnavailable(str(exc))

        warnings: List[str] = []
        if not items:
            warnings.append("No matches found. Try broadening your query.")
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
