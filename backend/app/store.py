from __future__ import annotations

from typing import Dict, List, Optional

from app.models import SearchResultItem


class ResultStore:
    """In-memory result store keyed by search_id (v1). The seam milestones 2-3 attach to."""

    def __init__(self) -> None:
        self._store: Dict[str, List[SearchResultItem]] = {}

    def save(self, search_id: str, results: List[SearchResultItem]) -> None:
        self._store[search_id] = results

    def get(self, search_id: str) -> Optional[List[SearchResultItem]]:
        return self._store.get(search_id)
