from __future__ import annotations

import re
import time
from datetime import date
from typing import List

import feedparser
import httpx

from app.models import CandidatePaper

ARXIV_API = "http://export.arxiv.org/api/query"
_VERSION_SUFFIX = re.compile(r"v\d+$")


class ArxivUnavailable(Exception):
    """Raised when arXiv cannot be reached after retries."""


class ArxivClient:
    def __init__(self, base_url: str = ARXIV_API, timeout: float = 10.0) -> None:
        self.base_url = base_url
        self.timeout = timeout

    def search(self, query: str, pool_size: int) -> List[CandidatePaper]:
        params = {
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": pool_size,
            "sortBy": "relevance",
            "sortOrder": "descending",
        }
        raw = self._fetch_with_retry(params)
        return self._parse(raw)

    def _fetch_with_retry(self, params: dict, retries: int = 1, backoff: float = 1.0) -> str:
        last_exc: Exception | None = None
        for attempt in range(retries + 1):
            try:
                resp = httpx.get(self.base_url, params=params, timeout=self.timeout)
                resp.raise_for_status()
                return resp.text
            except httpx.HTTPError as exc:
                last_exc = exc
                if attempt < retries:
                    time.sleep(backoff)
        raise ArxivUnavailable(str(last_exc))

    @staticmethod
    def _parse(raw: str) -> List[CandidatePaper]:
        feed = feedparser.parse(raw)
        papers: List[CandidatePaper] = []
        for index, entry in enumerate(feed.entries):
            abs_id = entry.id.rsplit("/abs/", 1)[-1]
            arxiv_id = _VERSION_SUFFIX.sub("", abs_id)
            authors = [a.get("name", "") for a in getattr(entry, "authors", [])]
            published = date(*entry.published_parsed[:3])
            papers.append(
                CandidatePaper(
                    arxiv_id=arxiv_id,
                    title=" ".join(entry.title.split()),
                    authors=authors,
                    abstract=" ".join(entry.summary.split()),
                    published=published,
                    url=entry.id,
                    relevance_rank=index,
                )
            )
        return papers
