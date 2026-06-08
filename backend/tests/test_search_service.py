from __future__ import annotations

from datetime import date

import pytest

from app.arxiv_client import ArxivUnavailable
from app.citation_client import CitationUnavailable
from app.models import CandidatePaper, SearchRequest, SortKey
from app.search_service import POOL_SIZE, SearchNotFound, SearchService, SearchSourceUnavailable
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
        self.requested = None

    def get_citation_counts(self, arxiv_ids):
        self.requested = list(arxiv_ids)
        if self.exc:
            raise self.exc
        return self.counts


def _paper(aid, rank_pos, published=date(2020, 1, 1)):
    return CandidatePaper(
        arxiv_id=aid,
        title=f"T{aid}",
        authors=["A"],
        abstract="x",
        published=published,
        url=f"http://arxiv.org/abs/{aid}",
        relevance_rank=rank_pos,
    )


def test_requests_fixed_pool_of_200():
    arxiv = FakeArxiv(papers=[_paper("a", 0)])
    svc = SearchService(arxiv, FakeCitations({"a": 1}), ResultStore())
    svc.search(SearchRequest(query="q", n=10))
    assert arxiv.pool_size == POOL_SIZE == 200


def test_enriches_all_candidates_and_stores_full_pool():
    arxiv = FakeArxiv(papers=[_paper("a", 0), _paper("b", 1), _paper("c", 2)])
    cit = FakeCitations({"a": 5, "b": 9, "c": 1})
    store = ResultStore()
    svc = SearchService(arxiv, cit, store)
    resp = svc.search(SearchRequest(query="q", n=2))

    assert cit.requested == ["a", "b", "c"]  # all candidates enriched
    assert resp.pool_size == 3               # full pool stored
    assert len(resp.results) == 2            # top n returned
    assert len(store.get(resp.search_id)) == 3


def test_initial_results_are_in_relevance_order():
    arxiv = FakeArxiv(papers=[_paper("a", 0), _paper("b", 1), _paper("c", 2)])
    svc = SearchService(arxiv, FakeCitations({"a": 1, "b": 999, "c": 5}), ResultStore())
    resp = svc.search(SearchRequest(query="q", n=3))
    assert [r.arxiv_id for r in resp.results] == ["a", "b", "c"]  # NOT citation order


def test_empty_arxiv_returns_friendly_warning_and_stores_empty():
    store = ResultStore()
    svc = SearchService(FakeArxiv(papers=[]), FakeCitations(), store)
    resp = svc.search(SearchRequest(query="q", n=5))
    assert resp.results == []
    assert any("broadening" in w for w in resp.warnings)
    assert store.get(resp.search_id) == []


def test_arxiv_failure_raises_search_source_unavailable():
    svc = SearchService(FakeArxiv(exc=ArxivUnavailable("down")), FakeCitations(), ResultStore())
    with pytest.raises(SearchSourceUnavailable):
        svc.search(SearchRequest(query="q", n=5))


def test_citation_failure_degrades_with_warning():
    arxiv = FakeArxiv(papers=[_paper("a", 0), _paper("b", 1)])
    svc = SearchService(arxiv, FakeCitations(exc=CitationUnavailable("429")), ResultStore())
    resp = svc.search(SearchRequest(query="q", n=2))
    assert len(resp.results) == 2
    assert all(r.citation_data_missing for r in resp.results)
    assert any("Citation data unavailable" in w for w in resp.warnings)


def test_resort_reads_store_and_sorts_by_citations():
    arxiv = FakeArxiv(papers=[_paper("a", 0), _paper("b", 1), _paper("c", 2)])
    store = ResultStore()
    svc = SearchService(arxiv, FakeCitations({"a": 5, "b": 999, "c": 50}), store)
    resp = svc.search(SearchRequest(query="q", n=3))

    out = svc.resort(resp.search_id, SortKey.citations, n=2)
    assert [r.arxiv_id for r in out] == ["b", "c"]


def test_resort_unknown_id_raises_search_not_found():
    svc = SearchService(FakeArxiv(papers=[]), FakeCitations(), ResultStore())
    with pytest.raises(SearchNotFound):
        svc.resort("nope", SortKey.citations, n=10)
