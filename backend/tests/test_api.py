from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient

from app.main import app, get_service
from app.models import SearchResponse, SearchResultItem
from app.search_service import SearchNotFound, SearchSourceUnavailable

client = TestClient(app)


def _item(aid, citations):
    return SearchResultItem(
        arxiv_id=aid,
        title=f"T{aid}",
        authors=["A"],
        abstract="x",
        published=date(2020, 1, 23),
        url=f"http://arxiv.org/abs/{aid}",
        citation_count=citations,
        citation_data_missing=False,
    )


class FakeService:
    def __init__(self, response=None, resort_result=None, search_exc=None, resort_exc=None):
        self.response = response
        self.resort_result = resort_result or []
        self.search_exc = search_exc
        self.resort_exc = resort_exc
        self.last_request = None
        self.resort_args = None

    def search(self, request):
        self.last_request = request
        if self.search_exc:
            raise self.search_exc
        return self.response

    def resort(self, search_id, sort_key, n):
        self.resort_args = (search_id, sort_key, n)
        if self.resort_exc:
            raise self.resort_exc
        return self.resort_result


def teardown_function():
    app.dependency_overrides.clear()


def test_health_returns_ok():
    assert client.get("/api/health").json() == {"status": "ok"}


def test_search_returns_relevance_results():
    resp = SearchResponse(
        search_id="sid1", results=[_item("a", 10)], pool_size=200, warnings=[]
    )
    fake = FakeService(response=resp)
    app.dependency_overrides[get_service] = lambda: fake

    r = client.post("/api/search", json={"query": "scaling laws", "n": 5})
    assert r.status_code == 200
    body = r.json()
    assert body["search_id"] == "sid1"
    assert body["pool_size"] == 200
    assert body["results"][0]["arxiv_id"] == "a"
    assert fake.last_request.query == "scaling laws"
    assert fake.last_request.n == 5


def test_search_defaults_n_when_omitted():
    resp = SearchResponse(search_id="sid1", results=[], pool_size=0, warnings=[])
    fake = FakeService(response=resp)
    app.dependency_overrides[get_service] = lambda: fake

    r = client.post("/api/search", json={"query": "x"})
    assert r.status_code == 200
    assert fake.last_request.n == 10


def test_search_validation_error_returns_422():
    r = client.post("/api/search", json={"query": "", "n": 5})
    assert r.status_code == 422


def test_search_source_unavailable_returns_503():
    fake = FakeService(search_exc=SearchSourceUnavailable("down"))
    app.dependency_overrides[get_service] = lambda: fake
    r = client.post("/api/search", json={"query": "x", "n": 5})
    assert r.status_code == 503


def test_resort_returns_sorted_results():
    fake = FakeService(resort_result=[_item("b", 999), _item("c", 50)])
    app.dependency_overrides[get_service] = lambda: fake

    r = client.get("/api/search/sid1", params={"sort": "citations", "n": 2})
    assert r.status_code == 200
    body = r.json()
    assert body["search_id"] == "sid1"
    assert [x["arxiv_id"] for x in body["results"]] == ["b", "c"]
    sid, sort_key, n = fake.resort_args
    assert sid == "sid1"
    assert sort_key.value == "citations"
    assert n == 2


def test_resort_defaults_to_relevance_and_n_10():
    fake = FakeService(resort_result=[])
    app.dependency_overrides[get_service] = lambda: fake
    r = client.get("/api/search/sid1")
    assert r.status_code == 200
    sid, sort_key, n = fake.resort_args
    assert sort_key.value == "relevance"
    assert n == 10


def test_resort_invalid_sort_returns_422():
    fake = FakeService(resort_result=[])
    app.dependency_overrides[get_service] = lambda: fake
    r = client.get("/api/search/sid1", params={"sort": "popularity"})
    assert r.status_code == 422


def test_resort_unknown_id_returns_404():
    fake = FakeService(resort_exc=SearchNotFound("sid1"))
    app.dependency_overrides[get_service] = lambda: fake
    r = client.get("/api/search/sid1", params={"sort": "citations"})
    assert r.status_code == 404
