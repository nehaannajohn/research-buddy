from __future__ import annotations

from datetime import date

import pytest

from app.arxiv_client import ArxivUnavailable
from app.citation_client import CitationUnavailable
from app.models import CandidatePaper, SearchRequest
from app.search_service import SearchService, SearchSourceUnavailable
from app.store import ResultStore


class FakeArxiv:
    def __init__(self, papers=None, exc=None):
        self.papers = papers or []
        self.exc = exc
        self.pool_size = None

    def search(self, query, pool_size):
        self.pool_size = pool_size
        if self.exc:
            raise self.exc
        return self.papers


class FakeCitations:
    def __init__(self, counts=None, exc=None):
        self.counts = counts or {}
        self.exc = exc

    def get_citation_counts(self, arxiv_ids):
        if self.exc:
            raise self.exc
        return self.counts


def _paper(aid, rank_pos):
    return CandidatePaper(
        arxiv_id=aid,
        title=f"T{aid}",
        authors=["A"],
        abstract="x",
        published=date(2022, 1, 1),
        url=f"http://arxiv.org/abs/{aid}",
        relevance_rank=rank_pos,
    )


def test_pool_size_is_max_50_or_n_times_5():
    arxiv = FakeArxiv(papers=[_paper("a", 0)])
    svc = SearchService(arxiv, FakeCitations({"a": 1}), ResultStore())
    svc.search(SearchRequest(query="q", n=3))
    assert arxiv.pool_size == 50  # max(50, 15)

    arxiv2 = FakeArxiv(papers=[_paper("a", 0)])
    svc2 = SearchService(arxiv2, FakeCitations({"a": 1}), ResultStore())
    svc2.search(SearchRequest(query="q", n=20))
    assert arxiv2.pool_size == 100  # max(50, 100)


def test_happy_path_returns_results_and_stores_them():
    arxiv = FakeArxiv(papers=[_paper("a", 0), _paper("b", 1)])
    store = ResultStore()
    svc = SearchService(arxiv, FakeCitations({"a": 10, "b": 5}), store)
    resp = svc.search(SearchRequest(query="q", n=2))

    assert len(resp.results) == 2
    assert resp.warnings == []
    assert store.get(resp.search_id) == resp.results


def test_empty_arxiv_returns_friendly_warning_not_error():
    svc = SearchService(FakeArxiv(papers=[]), FakeCitations(), ResultStore())
    resp = svc.search(SearchRequest(query="q", n=5))
    assert resp.results == []
    assert any("broadening" in w for w in resp.warnings)


def test_arxiv_failure_raises_search_source_unavailable():
    svc = SearchService(
        FakeArxiv(exc=ArxivUnavailable("down")), FakeCitations(), ResultStore()
    )
    with pytest.raises(SearchSourceUnavailable):
        svc.search(SearchRequest(query="q", n=5))


def test_citation_failure_degrades_gracefully_with_warning():
    arxiv = FakeArxiv(papers=[_paper("a", 0), _paper("b", 1)])
    svc = SearchService(
        arxiv, FakeCitations(exc=CitationUnavailable("rate limit")), ResultStore()
    )
    resp = svc.search(SearchRequest(query="q", n=2))

    assert len(resp.results) == 2
    assert all(r.citation_data_missing for r in resp.results)
    assert any("Citation data unavailable" in w for w in resp.warnings)
