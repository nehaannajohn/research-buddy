from __future__ import annotations

from datetime import date

import pytest

from app.models import SearchRequest, SearchResultItem, SortKey
from app.openalex_client import OpenAlexUnavailable
from app.search_service import POOL_SIZE, SearchNotFound, SearchService, SearchSourceUnavailable
from app.store import ResultStore


class FakeOpenAlex:
    def __init__(self, items=None, exc=None):
        self.items = items or []
        self.exc = exc
        self.pool_size = None

    def search(self, query, pool_size):
        self.pool_size = pool_size
        if self.exc:
            raise self.exc
        return self.items


def _item(aid, citations=0, published=date(2020, 1, 1)):
    return SearchResultItem(
        arxiv_id=aid,
        title=f"T{aid}",
        authors=["A"],
        abstract="x",
        published=published,
        url=f"http://arxiv.org/abs/{aid}",
        citation_count=citations,
        citation_data_missing=False,
    )


def test_requests_fixed_pool_of_200():
    oa = FakeOpenAlex(items=[_item("a")])
    svc = SearchService(oa, ResultStore())
    svc.search(SearchRequest(query="q", n=10))
    assert oa.pool_size == POOL_SIZE == 200


def test_stores_full_pool_and_returns_top_n_relevance_order():
    oa = FakeOpenAlex(items=[_item("a", 1), _item("b", 999), _item("c", 5)])
    store = ResultStore()
    svc = SearchService(oa, store)
    resp = svc.search(SearchRequest(query="q", n=2))
    assert resp.pool_size == 3
    assert len(resp.results) == 2
    # relevance (input) order preserved, NOT citation order
    assert [r.arxiv_id for r in resp.results] == ["a", "b"]
    assert len(store.get(resp.search_id)) == 3


def test_empty_returns_friendly_warning_and_stores_empty():
    store = ResultStore()
    svc = SearchService(FakeOpenAlex(items=[]), store)
    resp = svc.search(SearchRequest(query="q", n=5))
    assert resp.results == []
    assert any("broadening" in w for w in resp.warnings)
    assert store.get(resp.search_id) == []


def test_openalex_failure_raises_search_source_unavailable():
    svc = SearchService(FakeOpenAlex(exc=OpenAlexUnavailable("down")), ResultStore())
    with pytest.raises(SearchSourceUnavailable):
        svc.search(SearchRequest(query="q", n=5))


def test_resort_reads_store_and_sorts_by_citations():
    oa = FakeOpenAlex(items=[_item("a", 5), _item("b", 999), _item("c", 50)])
    store = ResultStore()
    svc = SearchService(oa, store)
    resp = svc.search(SearchRequest(query="q", n=3))
    out = svc.resort(resp.search_id, SortKey.citations, n=2)
    assert [r.arxiv_id for r in out] == ["b", "c"]


def test_resort_unknown_id_raises_search_not_found():
    svc = SearchService(FakeOpenAlex(items=[]), ResultStore())
    with pytest.raises(SearchNotFound):
        svc.resort("nope", SortKey.citations, n=10)
