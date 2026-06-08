from __future__ import annotations

import re
from typing import Dict, Iterator, List, Optional

import httpx

OPENALEX_WORKS = "https://api.openalex.org/works"

# arXiv mints a DOI for every paper in the form 10.48550/arXiv.<id>; OpenAlex
# stores it lower-cased (10.48550/arxiv.<id>) and indexes the work under it.
_ARXIV_DOI_PREFIX = "10.48550/arxiv."
# Capture the bare id, stopping at any query/fragment so a stray ?ver=2 or #frag
# in the DOI field can't corrupt the id we map back to.
_ARXIV_FROM_DOI = re.compile(r"10\.48550/arxiv\.([^\s?#]+)", re.IGNORECASE)

# OpenAlex allows up to 50 OR-separated values in a single filter.
_CHUNK_SIZE = 50


class CitationUnavailable(Exception):
    """Raised when the citation source cannot be reached or rate-limits."""


class CitationClient:
    """Looks up citation counts from OpenAlex, keyed by arXiv DOI.

    Returns ``{arxiv_id: cited_by_count}`` for the IDs OpenAlex resolves. IDs it
    does not return (e.g. preprints deduped into their published version) are
    simply omitted; the caller treats absent IDs as missing.
    """

    def __init__(
        self,
        base_url: str = OPENALEX_WORKS,
        timeout: float = 10.0,
        mailto: Optional[str] = None,
    ) -> None:
        self.base_url = base_url
        self.timeout = timeout
        # Supplying a contact email opts into OpenAlex's faster, more reliable
        # "polite pool". Optional — the API also works anonymously.
        self.mailto = mailto

    def get_citation_counts(self, arxiv_ids: List[str]) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for chunk in self._chunks(arxiv_ids, _CHUNK_SIZE):
            counts.update(self._fetch_chunk(chunk))
        return counts

    @staticmethod
    def _chunks(items: List[str], size: int) -> Iterator[List[str]]:
        for i in range(0, len(items), size):
            yield items[i : i + size]

    def _fetch_chunk(self, arxiv_ids: List[str]) -> Dict[str, int]:
        dois = [f"{_ARXIV_DOI_PREFIX}{aid}" for aid in arxiv_ids]
        params = {
            "filter": "doi:" + "|".join(dois),
            "select": "doi,cited_by_count",
            "per-page": _CHUNK_SIZE,
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
            raise CitationUnavailable(str(exc))

        counts: Dict[str, int] = {}
        for work in resp.json().get("results", []):
            match = _ARXIV_FROM_DOI.search(work.get("doi") or "")
            count = work.get("cited_by_count")
            if match and count is not None:
                counts[match.group(1)] = count
        return counts
