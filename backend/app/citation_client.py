from __future__ import annotations

from typing import Dict, List

import httpx

S2_BATCH = "https://api.semanticscholar.org/graph/v1/paper/batch"


class CitationUnavailable(Exception):
    """Raised when Semantic Scholar cannot be reached or rate-limits."""


class CitationClient:
    def __init__(self, base_url: str = S2_BATCH, timeout: float = 10.0) -> None:
        self.base_url = base_url
        self.timeout = timeout

    def get_citation_counts(self, arxiv_ids: List[str]) -> Dict[str, int]:
        if not arxiv_ids:
            return {}
        ids = [f"ARXIV:{aid}" for aid in arxiv_ids]
        try:
            resp = httpx.post(
                self.base_url,
                params={"fields": "citationCount"},
                json={"ids": ids},
                timeout=self.timeout,
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise CitationUnavailable(str(exc))

        data = resp.json()
        counts: Dict[str, int] = {}
        for arxiv_id, item in zip(arxiv_ids, data):
            if item is not None and item.get("citationCount") is not None:
                counts[arxiv_id] = item["citationCount"]
        return counts
