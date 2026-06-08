from __future__ import annotations

from datetime import date

import pytest

from app.arxiv_abstracts import ArxivAbstractsUnavailable
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


class FakeAbstracts:
    def __init__(self, abstracts=None, exc=None):
        self.abstracts = abstracts or {}
        self.exc = exc
        self.requested = None

    def get_abstracts(self, arxiv_ids):
        self.requested = list(arxiv_ids)
        if self.exc:
            raise self.exc
        return self.abstracts


def _item(aid, citations=0, published=date(2020, 1, 1), abstract="openalex-abstract"):
    return SearchResultItem(
        arxiv_id=aid,
        title=f"T{aid}",
        authors=["A"],
        abstract=abstract,
        published=published,
        url=f"http://arxiv.org/abs/{aid}",
        citation_count=citations,
        citation_data_missing=False,
    )


def test_requests_fixed_pool_of_200():
    oa = FakeOpenAlex(items=[_item("a")])
    svc = SearchService(oa, FakeAbstracts(), ResultStore())
    svc.search(SearchRequest(query="q", n=10))
    assert oa.pool_size == POOL_SIZE == 200


def test_stores_full_pool_and_returns_top_n_relevance_order():
    oa = FakeOpenAlex(items=[_item("a", 1), _item("b", 999), _item("c", 5)])
    store = ResultStore()
    svc = SearchService(oa, FakeAbstracts(), store)
    resp = svc.search(SearchRequest(query="q", n=2))
    assert resp.pool_size == 3
    assert len(resp.results) == 2
    assert [r.arxiv_id for r in resp.results] == ["a", "b"]
    assert len(store.get(resp.search_id)) == 3


def test_overlays_arxiv_abstracts_onto_items():
    oa = FakeOpenAlex(items=[_item("a"), _item("b")])
    abstracts = FakeAbstracts({"a": "real arXiv abstract for a"})
    store = ResultStore()
    svc = SearchService(oa, abstracts, store)
    resp = svc.search(SearchRequest(query="q", n=2))

    assert abstracts.requested == ["a", "b"]
    by_id = {r.arxiv_id: r for r in store.get(resp.search_id)}
    assert by_id["a"].abstract == "real arXiv abstract for a"   # overlaid
    assert by_id["b"].abstract == "openalex-abstract"           # no arXiv abstract -> kept


def test_abstract_failure_degrades_with_warning_keeping_openalex_abstract():
    oa = FakeOpenAlex(items=[_item("a")])
    svc = SearchService(oa, FakeAbstracts(exc=ArxivAbstractsUnavailable("down")), ResultStore())
    resp = svc.search(SearchRequest(query="q", n=1))
    assert resp.results[0].abstract == "openalex-abstract"
    assert any("Abstracts" in w for w in resp.warnings)


def test_empty_returns_friendly_warning_and_stores_empty():
    oa = FakeOpenAlex(items=[])
    abstracts = FakeAbstracts()
    store = ResultStore()
    svc = SearchService(oa, abstracts, store)
    resp = svc.search(SearchRequest(query="q", n=5))
    assert resp.results == []
    assert any("broadening" in w for w in resp.warnings)
    assert store.get(resp.search_id) == []
    assert abstracts.requested is None  # no abstract fetch when no results


def test_openalex_failure_raises_search_source_unavailable():
    svc = SearchService(FakeOpenAlex(exc=OpenAlexUnavailable("down")), FakeAbstracts(), ResultStore())
    with pytest.raises(SearchSourceUnavailable):
        svc.search(SearchRequest(query="q", n=5))


def test_resort_reads_store_and_sorts_by_citations():
    oa = FakeOpenAlex(items=[_item("a", 5), _item("b", 999), _item("c", 50)])
    store = ResultStore()
    svc = SearchService(oa, FakeAbstracts(), store)
    resp = svc.search(SearchRequest(query="q", n=3))
    out = svc.resort(resp.search_id, SortKey.citations, n=2)
    assert [r.arxiv_id for r in out] == ["b", "c"]


def test_resort_unknown_id_raises_search_not_found():
    svc = SearchService(FakeOpenAlex(items=[]), FakeAbstracts(), ResultStore())
    with pytest.raises(SearchNotFound):
        svc.resort("nope", SortKey.citations, n=10)
