from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient

from app.main import app, get_service
from app.models import SearchResponse, SearchResultItem, SubScores
from app.search_service import SearchSourceUnavailable

client = TestClient(app)


def _sample_response():
    item = SearchResultItem(
        arxiv_id="2001.11111",
        title="Scaling Laws",
        authors=["Jane Researcher"],
        abstract="abstract",
        published=date(2020, 1, 23),
        url="http://arxiv.org/abs/2001.11111",
        citation_count=100,
        sub_scores=SubScores(relevance=1.0, citations=0.9, recency=0.5),
        final_score=0.82,
        citation_data_missing=False,
    )
    return SearchResponse(search_id="sid1", results=[item], pool_size=50, warnings=[])


class FakeService:
    def __init__(self, response=None, exc=None):
        self.response = response
        self.exc = exc
        self.last_request = None

    def search(self, request):
        self.last_request = request
        if self.exc:
            raise self.exc
        return self.response


def teardown_function():
    app.dependency_overrides.clear()


def test_health_returns_ok():
    assert client.get("/api/health").json() == {"status": "ok"}


def test_search_returns_ranked_results():
    fake = FakeService(response=_sample_response())
    app.dependency_overrides[get_service] = lambda: fake

    resp = client.post("/api/search", json={"query": "scaling laws", "n": 5})
    assert resp.status_code == 200
    body = resp.json()
    assert body["search_id"] == "sid1"
    assert body["results"][0]["sub_scores"]["citations"] == 0.9
    assert fake.last_request.query == "scaling laws"
    assert fake.last_request.n == 5


def test_search_validation_error_returns_422():
    resp = client.post("/api/search", json={"query": "", "n": 5})
    assert resp.status_code == 422


def test_search_source_unavailable_returns_503():
    fake = FakeService(exc=SearchSourceUnavailable("down"))
    app.dependency_overrides[get_service] = lambda: fake

    resp = client.post("/api/search", json={"query": "x", "n": 5})
    assert resp.status_code == 503
