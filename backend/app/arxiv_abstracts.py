from __future__ import annotations

import re
from typing import Dict, Iterator, List

import feedparser
import httpx

ARXIV_API = "https://export.arxiv.org/api/query"
_VERSION_SUFFIX = re.compile(r"v\d+$")
_CHUNK = 100


class ArxivAbstractsUnavailable(Exception):
    """Raised when arXiv abstract lookup fails."""


class ArxivAbstractClient:
    def __init__(self, base_url: str = ARXIV_API, timeout: float = 15.0) -> None:
        self.base_url = base_url
        self.timeout = timeout

    def get_abstracts(self, arxiv_ids: List[str]) -> Dict[str, str]:
        abstracts: Dict[str, str] = {}
        for chunk in self._chunks(arxiv_ids, _CHUNK):
            abstracts.update(self._fetch_chunk(chunk))
        return abstracts

    @staticmethod
    def _chunks(items: List[str], size: int) -> Iterator[List[str]]:
        for i in range(0, len(items), size):
            yield items[i : i + size]

    def _fetch_chunk(self, arxiv_ids: List[str]) -> Dict[str, str]:
        try:
            resp = httpx.get(
                self.base_url,
                params={"id_list": ",".join(arxiv_ids), "max_results": len(arxiv_ids)},
                timeout=self.timeout,
                follow_redirects=True,
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise ArxivAbstractsUnavailable(str(exc))

        feed = feedparser.parse(resp.text)
        abstracts: Dict[str, str] = {}
        for entry in feed.entries:
            abs_id = entry.id.rsplit("/abs/", 1)[-1]
            arxiv_id = _VERSION_SUFFIX.sub("", abs_id)
            abstracts[arxiv_id] = " ".join(entry.summary.split())
        return abstracts
