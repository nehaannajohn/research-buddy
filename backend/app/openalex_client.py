from __future__ import annotations

import re
from datetime import date
from typing import List, Optional

import httpx

from app.models import SearchResultItem

OPENALEX_WORKS = "https://api.openalex.org/works"
ARXIV_SOURCE_ID = "s4306400194"  # OpenAlex source id for arXiv
_ARXIV_FROM_DOI = re.compile(r"10\.48550/arxiv\.([^\s?#]+)", re.IGNORECASE)
_SELECT = (
    "doi,title,authorships,publication_date,cited_by_count,"
    "abstract_inverted_index,primary_location"
)


class OpenAlexUnavailable(Exception):
    """Raised when OpenAlex cannot be reached or rate-limits."""


def _reconstruct_abstract(inverted_index: Optional[dict]) -> str:
    """Rebuild plain-text abstract from OpenAlex's {word: [positions]} index."""
    if not inverted_index:
        return ""
    positions = [p for ps in inverted_index.values() for p in ps]
    if not positions:
        return ""
    words = [""] * (max(positions) + 1)
    for word, ps in inverted_index.items():
        for p in ps:
            words[p] = word
    return " ".join(w for w in words if w)


class OpenAlexClient:
    def __init__(
        self,
        base_url: str = OPENALEX_WORKS,
        timeout: float = 15.0,
        mailto: Optional[str] = None,
    ) -> None:
        self.base_url = base_url
        self.timeout = timeout
        self.mailto = mailto

    def search(self, query: str, pool_size: int) -> List[SearchResultItem]:
        params = {
            "search": query,
            "filter": f"primary_location.source.id:{ARXIV_SOURCE_ID}",
            "per-page": min(pool_size, 200),
            "select": _SELECT,
        }
        if self.mailto:
            params["mailto"] = self.mailto
        try:
            resp = httpx.get(
                self.base_url,
                params=params,
                timeout=self.timeout,
                follow_redirects=True,
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise OpenAlexUnavailable(str(exc))

        items: List[SearchResultItem] = []
        for work in resp.json().get("results", []):
            arxiv_id = self._arxiv_id(work)
            if arxiv_id is None:
                continue
            items.append(self._to_item(work, arxiv_id))
        return items

    @staticmethod
    def _arxiv_id(work: dict) -> Optional[str]:
        match = _ARXIV_FROM_DOI.search(work.get("doi") or "")
        return match.group(1) if match else None

    @staticmethod
    def _to_item(work: dict, arxiv_id: str) -> SearchResultItem:
        location = work.get("primary_location") or {}
        url = location.get("landing_page_url") or f"https://arxiv.org/abs/{arxiv_id}"
        authors = [
            a.get("author", {}).get("display_name", "")
            for a in work.get("authorships", [])
        ]
        published_str = work.get("publication_date")
        published = date.fromisoformat(published_str) if published_str else date.min
        return SearchResultItem(
            arxiv_id=arxiv_id,
            title=" ".join((work.get("title") or "").split()),
            authors=authors,
            abstract=_reconstruct_abstract(work.get("abstract_inverted_index")),
            published=published,
            url=url,
            citation_count=work.get("cited_by_count") or 0,
            citation_data_missing=False,
        )
