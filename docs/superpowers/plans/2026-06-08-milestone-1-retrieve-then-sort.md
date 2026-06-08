# Milestone 1 Redesign: Retrieve-then-Sort — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the weighted-ranking model with a retrieve-then-sort model: fetch top 200 arXiv candidates by relevance, enrich all with OpenAlex citations once, store under a `search_id`, and let the user re-sort the stored pool by citations or recency (top N, default 10) with no new network calls.

**Architecture:** Reuses the existing `ArxivClient`, `CitationClient`, and `ResultStore` unchanged. Replaces the pure `Ranker` (weighted scoring) with a pure `Sorter` (single-key stable sort). `SearchService` gains a `resort` path that reads the stored pool. A new `GET /api/search/{search_id}` endpoint exposes re-sorting. The React app drops the weight sliders and adds a Citations/Recency toggle plus a result-count selector that drive the re-sort endpoint.

**Tech Stack:** Python 3.9, FastAPI, pydantic v2, pytest (backend). Vite + React 19 + TypeScript, Vitest, React Testing Library (frontend).

**Working directory:** `/Users/nehajohn/Desktop/research-buddy/.worktrees/milestone-1-discovery-ranking` (git worktree on branch `milestone-1-discovery-ranking`). Backend venv: `backend/.venv`. Run backend tests from `backend/` as `.venv/bin/pytest`; frontend tests from `frontend/` as `npm test`. All paths below are relative to the working directory.

---

## File Structure

### Backend (`backend/app/`)
- `models.py` — **modify.** Remove `Weights`, `SubScores`. Simplify `SearchRequest` (drop `weights`, give `n` a default of 10) and `SearchResultItem` (drop `sub_scores`, `final_score`). Add `SortKey` enum and `ResortResponse`.
- `sorter.py` — **create.** Pure functions `build_result_items()` and `sort_papers()`. Replaces `ranker.py`.
- `ranker.py` — **delete.**
- `search_service.py` — **modify.** Fixed pool of 200, enrich all, store full pool, return relevance order; add `resort()` and `SearchNotFound`.
- `main.py` — **modify.** New `POST` body shape; add `GET /api/search/{search_id}`.
- `arxiv_client.py`, `citation_client.py`, `store.py` — **unchanged.**

### Backend tests (`backend/tests/`)
- `test_models.py` — **modify.** Drop `Weights`/`SubScores` tests; update shapes; add `SortKey` test.
- `test_sorter.py` — **create.** Replaces `test_ranker.py`.
- `test_ranker.py` — **delete.**
- `test_search_service.py` — **modify (full rewrite).**
- `test_api.py` — **modify (full rewrite).**
- `test_arxiv_client.py`, `test_citation_client.py`, `test_store.py`, `test_live_smoke.py` — **unchanged.**

### Frontend (`frontend/src/`)
- `types.ts` — **modify.** Remove `Weights`, `SubScores`; simplify `SearchResultItem`; add `SortKey`, `ResortResponse`.
- `api.ts` — **modify.** `searchPapers(query, n)` (drop weights); add `resortPapers(searchId, sort, n)`.
- `components/ResultCard.tsx` — **modify.** Remove score breakdown.
- `components/SearchBar.tsx` — **modify.** Controlled result-count selector (5/10/25).
- `components/SortControl.tsx` — **create.** Citations/Recency toggle.
- `components/WeightSliders.tsx` — **delete.**
- `components/ResultList.tsx` — **unchanged.**
- `App.tsx` — **modify.** Sort + count state, re-sort wiring, expired-search handling.

### Frontend tests (`frontend/src/__tests__/`)
- `api.test.ts`, `ResultCard.test.tsx`, `SearchBar.test.tsx`, `App.test.tsx` — **modify.**
- `SortControl.test.tsx` — **create.**

### Docs
- `CLAUDE.md`, `README.md` — **modify** (final task).

---

## Task 1: Simplify data models + add SortKey

**Files:**
- Modify: `backend/app/models.py`
- Modify: `backend/tests/test_models.py`

- [ ] **Step 1: Replace the contents of `backend/tests/test_models.py`**

```python
from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from app.models import (
    CandidatePaper,
    SearchRequest,
    SearchResponse,
    SearchResultItem,
    SortKey,
)


def test_search_request_defaults_n_to_10():
    assert SearchRequest(query="scaling laws").n == 10


def test_search_request_rejects_empty_query():
    with pytest.raises(ValidationError):
        SearchRequest(query="", n=5)


def test_search_request_rejects_non_positive_n():
    with pytest.raises(ValidationError):
        SearchRequest(query="scaling laws", n=0)


def test_search_request_has_no_weights_field():
    assert "weights" not in SearchRequest.model_fields


def test_sort_key_values():
    assert {s.value for s in SortKey} == {"relevance", "citations", "recency"}


def test_result_item_has_no_score_fields():
    fields = SearchResultItem.model_fields
    assert "sub_scores" not in fields
    assert "final_score" not in fields


def test_result_item_roundtrip():
    item = SearchResultItem(
        arxiv_id="2001.08361",
        title="Scaling Laws for Neural Language Models",
        authors=["Jared Kaplan"],
        abstract="abstract",
        published=date(2020, 1, 23),
        url="http://arxiv.org/abs/2001.08361",
        citation_count=1504,
        citation_data_missing=False,
    )
    assert item.citation_count == 1504
    assert item.citation_data_missing is False


def test_search_response_holds_results():
    item = SearchResultItem(
        arxiv_id="2001.08361",
        title="A Paper",
        authors=["A"],
        abstract="x",
        published=date(2020, 1, 23),
        url="http://arxiv.org/abs/2001.08361",
        citation_count=10,
        citation_data_missing=False,
    )
    resp = SearchResponse(search_id="abc", results=[item], pool_size=200, warnings=[])
    assert resp.pool_size == 200
    assert resp.results[0].arxiv_id == "2001.08361"
```

- [ ] **Step 2: Run the test to verify it fails**

Run from `backend/`: `.venv/bin/pytest tests/test_models.py -v`
Expected: FAIL — `ImportError: cannot import name 'SortKey'` (and assertion failures for removed fields).

- [ ] **Step 3: Replace the contents of `backend/app/models.py`**

```python
from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel, Field


class SortKey(str, Enum):
    relevance = "relevance"
    citations = "citations"
    recency = "recency"


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    n: int = Field(default=10, ge=1, le=100)


class CandidatePaper(BaseModel):
    arxiv_id: str
    title: str
    authors: list[str]
    abstract: str
    published: date
    url: str
    relevance_rank: int  # 0-based; 0 = most relevant (arXiv order)


class SearchResultItem(BaseModel):
    arxiv_id: str
    title: str
    authors: list[str]
    abstract: str
    published: date
    url: str
    citation_count: int
    citation_data_missing: bool


class SearchResponse(BaseModel):
    search_id: str
    results: list[SearchResultItem]
    pool_size: int
    warnings: list[str]


class ResortResponse(BaseModel):
    search_id: str
    results: list[SearchResultItem]
    warnings: list[str]
```

- [ ] **Step 4: Run the test to verify it passes**

Run from `backend/`: `.venv/bin/pytest tests/test_models.py -v`
Expected: PASS (8 passed).

- [ ] **Step 5: Commit**

```bash
cd /Users/nehajohn/Desktop/research-buddy/.worktrees/milestone-1-discovery-ranking
git add backend/app/models.py backend/tests/test_models.py
git commit -m "refactor(backend): simplify models for retrieve-then-sort (drop weights/scores, add SortKey)"
```

---

## Task 2: Sorter (pure function) replacing Ranker

**Files:**
- Create: `backend/app/sorter.py`
- Create: `backend/tests/test_sorter.py`
- Delete: `backend/app/ranker.py`
- Delete: `backend/tests/test_ranker.py`

- [ ] **Step 1: Delete the old Ranker and its tests**

```bash
cd /Users/nehajohn/Desktop/research-buddy/.worktrees/milestone-1-discovery-ranking
git rm backend/app/ranker.py backend/tests/test_ranker.py
```

- [ ] **Step 2: Create the failing test `backend/tests/test_sorter.py`**

```python
from __future__ import annotations

from datetime import date

from app.models import CandidatePaper, SortKey
from app.sorter import build_result_items, sort_papers


def _candidate(aid, rank_pos, published=date(2020, 1, 1)):
    return CandidatePaper(
        arxiv_id=aid,
        title=f"T{aid}",
        authors=["A"],
        abstract="x",
        published=published,
        url=f"http://arxiv.org/abs/{aid}",
        relevance_rank=rank_pos,
    )


def test_build_result_items_preserves_order_and_flags_missing():
    cands = [_candidate("a", 0), _candidate("b", 1)]
    items = build_result_items(cands, {"a": 5})
    assert [i.arxiv_id for i in items] == ["a", "b"]  # arXiv order preserved
    assert items[0].citation_count == 5 and items[0].citation_data_missing is False
    assert items[1].citation_count == 0 and items[1].citation_data_missing is True


def test_sort_relevance_is_identity():
    cands = [_candidate("a", 0), _candidate("b", 1), _candidate("c", 2)]
    items = build_result_items(cands, {})
    out = sort_papers(items, SortKey.relevance, n=3)
    assert [i.arxiv_id for i in out] == ["a", "b", "c"]


def test_sort_citations_descending():
    cands = [_candidate("a", 0), _candidate("b", 1), _candidate("c", 2)]
    items = build_result_items(cands, {"a": 5, "b": 100, "c": 20})
    out = sort_papers(items, SortKey.citations, n=3)
    assert [i.arxiv_id for i in out] == ["b", "c", "a"]


def test_sort_recency_descending():
    cands = [
        _candidate("old", 0, published=date(2018, 1, 1)),
        _candidate("new", 1, published=date(2024, 1, 1)),
        _candidate("mid", 2, published=date(2021, 1, 1)),
    ]
    items = build_result_items(cands, {})
    out = sort_papers(items, SortKey.recency, n=3)
    assert [i.arxiv_id for i in out] == ["new", "mid", "old"]


def test_sort_is_stable_on_ties_preserving_relevance_order():
    # all citation counts equal -> order must stay arXiv (relevance) order
    cands = [_candidate("a", 0), _candidate("b", 1), _candidate("c", 2)]
    items = build_result_items(cands, {"a": 0, "b": 0, "c": 0})
    out = sort_papers(items, SortKey.citations, n=3)
    assert [i.arxiv_id for i in out] == ["a", "b", "c"]


def test_sort_truncates_to_n():
    cands = [_candidate(str(i), i) for i in range(5)]
    items = build_result_items(cands, {})
    out = sort_papers(items, SortKey.relevance, n=2)
    assert [i.arxiv_id for i in out] == ["0", "1"]


def test_sort_n_larger_than_pool_returns_all():
    cands = [_candidate("a", 0), _candidate("b", 1)]
    items = build_result_items(cands, {})
    out = sort_papers(items, SortKey.citations, n=10)
    assert len(out) == 2


def test_sort_empty_pool_returns_empty():
    assert sort_papers([], SortKey.citations, n=10) == []
```

- [ ] **Step 3: Run the test to verify it fails**

Run from `backend/`: `.venv/bin/pytest tests/test_sorter.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.sorter'`.

- [ ] **Step 4: Create `backend/app/sorter.py`**

```python
from __future__ import annotations

from typing import Dict, List

from app.models import CandidatePaper, SearchResultItem, SortKey


def build_result_items(
    candidates: List[CandidatePaper], citation_counts: Dict[str, int]
) -> List[SearchResultItem]:
    """Combine arXiv candidates with citation counts, preserving arXiv (relevance) order.

    IDs absent from ``citation_counts`` get count 0 and are flagged as missing.
    """
    items: List[SearchResultItem] = []
    for c in candidates:
        items.append(
            SearchResultItem(
                arxiv_id=c.arxiv_id,
                title=c.title,
                authors=c.authors,
                abstract=c.abstract,
                published=c.published,
                url=c.url,
                citation_count=citation_counts.get(c.arxiv_id, 0),
                citation_data_missing=c.arxiv_id not in citation_counts,
            )
        )
    return items


def sort_papers(
    items: List[SearchResultItem], sort_key: SortKey, n: int
) -> List[SearchResultItem]:
    """Return the top ``n`` items sorted by ``sort_key``.

    ``relevance`` keeps the input (arXiv) order. ``citations`` and ``recency`` use a
    stable descending sort, so ties preserve the underlying relevance order.
    """
    if sort_key == SortKey.citations:
        ordered = sorted(items, key=lambda it: it.citation_count, reverse=True)
    elif sort_key == SortKey.recency:
        ordered = sorted(items, key=lambda it: it.published, reverse=True)
    else:  # SortKey.relevance — input is already in arXiv order
        ordered = list(items)
    return ordered[:n]
```

- [ ] **Step 5: Run the test to verify it passes**

Run from `backend/`: `.venv/bin/pytest tests/test_sorter.py -v`
Expected: PASS (8 passed).

- [ ] **Step 6: Commit**

```bash
cd /Users/nehajohn/Desktop/research-buddy/.worktrees/milestone-1-discovery-ranking
git add backend/app/sorter.py backend/tests/test_sorter.py backend/app/ranker.py backend/tests/test_ranker.py
git commit -m "feat(backend): add pure Sorter (build + single-key stable sort), remove Ranker"
```

---

## Task 3: SearchService — fixed 200 pool, enrich-all, store, resort

**Files:**
- Modify: `backend/app/search_service.py` (full replace)
- Modify: `backend/tests/test_search_service.py` (full replace)

- [ ] **Step 1: Replace the contents of `backend/tests/test_search_service.py`**

```python
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
```

- [ ] **Step 2: Run the test to verify it fails**

Run from `backend/`: `.venv/bin/pytest tests/test_search_service.py -v`
Expected: FAIL — `ImportError: cannot import name 'POOL_SIZE'` / `SearchNotFound`.

- [ ] **Step 3: Replace the contents of `backend/app/search_service.py`**

```python
from __future__ import annotations

import uuid
from typing import Dict, List

from app.arxiv_client import ArxivUnavailable
from app.citation_client import CitationUnavailable
from app.models import SearchRequest, SearchResponse, SearchResultItem, SortKey
from app.sorter import build_result_items, sort_papers
from app.store import ResultStore

POOL_SIZE = 200


class SearchSourceUnavailable(Exception):
    """Raised when the primary source (arXiv) is unavailable."""


class SearchNotFound(Exception):
    """Raised when a search_id is not present in the store (unknown or expired)."""


class SearchService:
    def __init__(self, arxiv_client, citation_client, store: ResultStore) -> None:
        self.arxiv_client = arxiv_client
        self.citation_client = citation_client
        self.store = store

    def search(self, request: SearchRequest) -> SearchResponse:
        try:
            candidates = self.arxiv_client.search(request.query, POOL_SIZE)
        except ArxivUnavailable as exc:
            raise SearchSourceUnavailable(str(exc))

        warnings: List[str] = []

        if not candidates:
            warnings.append("No matches found. Try broadening your query.")
            return self._store_and_respond([], warnings, request.n)

        try:
            citation_counts: Dict[str, int] = self.citation_client.get_citation_counts(
                [c.arxiv_id for c in candidates]
            )
        except CitationUnavailable:
            citation_counts = {}
            warnings.append(
                "Citation data unavailable — sorting by citations may be incomplete."
            )

        items = build_result_items(candidates, citation_counts)
        return self._store_and_respond(items, warnings, request.n)

    def resort(self, search_id: str, sort_key: SortKey, n: int) -> List[SearchResultItem]:
        items = self.store.get(search_id)
        if items is None:
            raise SearchNotFound(search_id)
        return sort_papers(items, sort_key, n)

    def _store_and_respond(
        self, items: List[SearchResultItem], warnings: List[str], n: int
    ) -> SearchResponse:
        search_id = uuid.uuid4().hex
        self.store.save(search_id, items)
        results = sort_papers(items, SortKey.relevance, n)
        return SearchResponse(
            search_id=search_id,
            results=results,
            pool_size=len(items),
            warnings=warnings,
        )
```

- [ ] **Step 4: Run the test to verify it passes**

Run from `backend/`: `.venv/bin/pytest tests/test_search_service.py -v`
Expected: PASS (8 passed).

- [ ] **Step 5: Commit**

```bash
cd /Users/nehajohn/Desktop/research-buddy/.worktrees/milestone-1-discovery-ranking
git add backend/app/search_service.py backend/tests/test_search_service.py
git commit -m "feat(backend): retrieve-then-sort SearchService (200 pool, enrich-all, store, resort)"
```

---

## Task 4: API — new POST shape + GET re-sort endpoint

**Files:**
- Modify: `backend/app/main.py` (full replace)
- Modify: `backend/tests/test_api.py` (full replace)

- [ ] **Step 1: Replace the contents of `backend/tests/test_api.py`**

```python
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
```

- [ ] **Step 2: Run the test to verify it fails**

Run from `backend/`: `.venv/bin/pytest tests/test_api.py -v`
Expected: FAIL — `ImportError: cannot import name 'SearchNotFound'` and missing GET route.

- [ ] **Step 3: Replace the contents of `backend/app/main.py`**

```python
from __future__ import annotations

import os

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.arxiv_client import ArxivClient
from app.citation_client import CitationClient
from app.models import ResortResponse, SearchRequest, SearchResponse, SortKey
from app.search_service import SearchNotFound, SearchService, SearchSourceUnavailable
from app.store import ResultStore

app = FastAPI(title="Research Buddy")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_store = ResultStore()
# OPENALEX_MAILTO opts into OpenAlex's faster "polite pool" when set.
_service = SearchService(
    ArxivClient(),
    CitationClient(mailto=os.getenv("OPENALEX_MAILTO")),
    _store,
)


def get_service() -> SearchService:
    return _service


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/search", response_model=SearchResponse)
def search(
    request: SearchRequest, service: SearchService = Depends(get_service)
) -> SearchResponse:
    try:
        return service.search(request)
    except SearchSourceUnavailable:
        raise HTTPException(
            status_code=503, detail="Search source unavailable, please retry."
        )


@app.get("/api/search/{search_id}", response_model=ResortResponse)
def resort(
    search_id: str,
    sort: SortKey = SortKey.relevance,
    n: int = Query(default=10, ge=1, le=100),
    service: SearchService = Depends(get_service),
) -> ResortResponse:
    try:
        results = service.resort(search_id, sort, n)
    except SearchNotFound:
        raise HTTPException(status_code=404, detail="Search expired, please search again.")
    return ResortResponse(search_id=search_id, results=results, warnings=[])
```

- [ ] **Step 4: Run the test to verify it passes**

Run from `backend/`: `.venv/bin/pytest tests/test_api.py -v`
Expected: PASS (9 passed).

- [ ] **Step 5: Run the full backend suite**

Run from `backend/`: `.venv/bin/pytest -q`
Expected: PASS — all tests across models, sorter, arxiv_client, citation_client, store, search_service, api pass; live smoke tests skipped (2 skipped).

- [ ] **Step 6: Commit**

```bash
cd /Users/nehajohn/Desktop/research-buddy/.worktrees/milestone-1-discovery-ranking
git add backend/app/main.py backend/tests/test_api.py
git commit -m "feat(backend): new POST /api/search shape + GET /api/search/{id} re-sort endpoint"
```

---

## Task 5: Backend live verification (no new code)

**Files:** none (verification only).

- [ ] **Step 1: Start the server on a test port**

```bash
cd /Users/nehajohn/Desktop/research-buddy/.worktrees/milestone-1-discovery-ranking/backend
OPENALEX_MAILTO="nehaannajohn@gmail.com" .venv/bin/uvicorn app.main:app --port 8750 > /tmp/rb_verify.log 2>&1 &
sleep 3 && curl -s http://127.0.0.1:8750/api/health
```
Expected: `{"status":"ok"}`.

- [ ] **Step 2: Search, then re-sort by citations, and confirm the Kaplan paper surfaces**

```bash
SID=$(curl -s -X POST http://127.0.0.1:8750/api/search -H 'Content-Type: application/json' \
  -d '{"query":"scaling laws","n":10}' | python3 -c "import sys,json;print(json.load(sys.stdin)['search_id'])")
echo "search_id=$SID"
curl -s "http://127.0.0.1:8750/api/search/$SID?sort=citations&n=10" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); [print(r['citation_count'],r['title'][:55]) for r in d['results']]"
```
Expected: results sorted by citation count descending; "Scaling Laws for Neural Language Models" appears near the top (it is in the 200-pool and is highly cited). Re-sorting makes no new arXiv/OpenAlex calls.

- [ ] **Step 3: Confirm an unknown search_id returns 404**

```bash
curl -s -o /dev/null -w "%{http_code}\n" "http://127.0.0.1:8750/api/search/deadbeef?sort=citations"
```
Expected: `404`.

- [ ] **Step 4: Stop the server**

```bash
lsof -ti tcp:8750 | xargs kill -9 2>/dev/null; echo stopped
```

(No commit — verification only.)

---

## Task 6: Frontend types

**Files:**
- Modify: `frontend/src/types.ts`

- [ ] **Step 1: Replace the contents of `frontend/src/types.ts`**

```ts
export type SortKey = "relevance" | "citations" | "recency";

export interface SearchResultItem {
  arxiv_id: string;
  title: string;
  authors: string[];
  abstract: string;
  published: string;
  url: string;
  citation_count: number;
  citation_data_missing: boolean;
}

export interface SearchResponse {
  search_id: string;
  results: SearchResultItem[];
  pool_size: number;
  warnings: string[];
}

export interface ResortResponse {
  search_id: string;
  results: SearchResultItem[];
  warnings: string[];
}
```

- [ ] **Step 2: Verify the build still type-checks (other files may break until later tasks)**

Run from `frontend/`: `npx tsc --noEmit`
Expected: errors ONLY in files that still reference removed types (`api.ts`, `App.tsx`, `ResultCard.tsx`, `WeightSliders.tsx`). `types.ts` itself has no errors. This is expected mid-refactor; later tasks fix the consumers.

- [ ] **Step 3: Commit**

```bash
cd /Users/nehajohn/Desktop/research-buddy/.worktrees/milestone-1-discovery-ranking
git add frontend/src/types.ts
git commit -m "refactor(frontend): simplify types for retrieve-then-sort (drop weights/scores, add SortKey)"
```

---

## Task 7: Frontend API client — searchPapers + resortPapers

**Files:**
- Modify: `frontend/src/api.ts`
- Modify: `frontend/src/__tests__/api.test.ts`

- [ ] **Step 1: Replace the contents of `frontend/src/__tests__/api.test.ts`**

```ts
import { afterEach, describe, expect, it, vi } from "vitest";
import { resortPapers, searchPapers } from "../api";
import type { ResortResponse, SearchResponse } from "../types";

afterEach(() => {
  vi.restoreAllMocks();
});

const searchSample: SearchResponse = {
  search_id: "sid1",
  results: [],
  pool_size: 200,
  warnings: [],
};

const resortSample: ResortResponse = {
  search_id: "sid1",
  results: [],
  warnings: [],
};

describe("searchPapers", () => {
  it("POSTs query and n, returns parsed JSON", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify(searchSample), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    const result = await searchPapers("scaling laws", 10);
    expect(result.search_id).toBe("sid1");

    const [url, options] = fetchMock.mock.calls[0];
    expect(String(url)).toMatch(/\/api\/search$/);
    expect(options.method).toBe("POST");
    expect(JSON.parse(options.body as string)).toEqual({ query: "scaling laws", n: 10 });
  });

  it("throws on non-ok response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response("nope", { status: 503 }))
    );
    await expect(searchPapers("x", 10)).rejects.toThrow("503");
  });
});

describe("resortPapers", () => {
  it("GETs the re-sort endpoint with sort and n", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify(resortSample), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await resortPapers("sid1", "citations", 25);

    const [url, options] = fetchMock.mock.calls[0];
    expect(String(url)).toContain("/api/search/sid1");
    expect(String(url)).toContain("sort=citations");
    expect(String(url)).toContain("n=25");
    expect(options?.method ?? "GET").toBe("GET");
  });

  it("throws an expired error on 404", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response("gone", { status: 404 }))
    );
    await expect(resortPapers("sid1", "citations", 10)).rejects.toThrow(/expired/i);
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run from `frontend/`: `npm test`
Expected: FAIL — `resortPapers` is not exported / `searchPapers` signature mismatch.

- [ ] **Step 3: Replace the contents of `frontend/src/api.ts`**

```ts
import type { ResortResponse, SearchResponse, SortKey } from "./types";

const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export async function searchPapers(query: string, n: number): Promise<SearchResponse> {
  const res = await fetch(`${BASE_URL}/api/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, n }),
  });
  if (!res.ok) {
    throw new Error(`Search failed (${res.status})`);
  }
  return (await res.json()) as SearchResponse;
}

export async function resortPapers(
  searchId: string,
  sort: SortKey,
  n: number
): Promise<ResortResponse> {
  const params = new URLSearchParams({ sort, n: String(n) });
  const res = await fetch(`${BASE_URL}/api/search/${searchId}?${params}`);
  if (res.status === 404) {
    throw new Error("Search expired — please search again.");
  }
  if (!res.ok) {
    throw new Error(`Sort failed (${res.status})`);
  }
  return (await res.json()) as ResortResponse;
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run from `frontend/`: `npm test`
Expected: the api tests pass. (Other suites — ResultCard/SearchBar/App — may still fail; later tasks fix them.)

- [ ] **Step 5: Commit**

```bash
cd /Users/nehajohn/Desktop/research-buddy/.worktrees/milestone-1-discovery-ranking
git add frontend/src/api.ts frontend/src/__tests__/api.test.ts
git commit -m "feat(frontend): searchPapers(query,n) + resortPapers(id,sort,n) with 404 handling"
```

---

## Task 8: ResultCard — remove score breakdown

**Files:**
- Modify: `frontend/src/components/ResultCard.tsx`
- Modify: `frontend/src/__tests__/ResultCard.test.tsx`

- [ ] **Step 1: Replace the contents of `frontend/src/__tests__/ResultCard.test.tsx`**

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ResultCard } from "../components/ResultCard";
import type { SearchResultItem } from "../types";

const item: SearchResultItem = {
  arxiv_id: "2001.08361",
  title: "Scaling Laws for Neural Language Models",
  authors: ["Jared Kaplan", "Sam McCandlish"],
  abstract: "We study empirical scaling laws.",
  published: "2020-01-23",
  url: "http://arxiv.org/abs/2001.08361",
  citation_count: 1504,
  citation_data_missing: false,
};

describe("ResultCard", () => {
  it("renders the title linked to arXiv", () => {
    render(<ResultCard item={item} />);
    const link = screen.getByRole("link", {
      name: /Scaling Laws for Neural Language Models/i,
    });
    expect(link).toHaveAttribute("href", "http://arxiv.org/abs/2001.08361");
  });

  it("shows the citation count and date", () => {
    render(<ResultCard item={item} />);
    expect(screen.getByText(/1504/)).toBeInTheDocument();
    expect(screen.getByText(/2020-01-23/)).toBeInTheDocument();
  });

  it("does not render a score breakdown", () => {
    render(<ResultCard item={item} />);
    expect(screen.queryByText(/relevance/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/recency/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/score/i)).not.toBeInTheDocument();
  });

  it("shows a flag badge when citation data is missing", () => {
    render(<ResultCard item={{ ...item, citation_data_missing: true }} />);
    expect(screen.getByText(/citation data unavailable/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run from `frontend/`: `npm test`
Expected: FAIL — the current `ResultCard` still renders the `relevance`/`recency`/`score` breakdown, so `test does not render a score breakdown` fails.

- [ ] **Step 3: Replace the contents of `frontend/src/components/ResultCard.tsx`**

```tsx
import type { SearchResultItem } from "../types";

export function ResultCard({ item }: { item: SearchResultItem }) {
  return (
    <article className="result-card">
      <h3>
        <a href={item.url} target="_blank" rel="noreferrer">
          {item.title}
        </a>
      </h3>
      <p className="authors">{item.authors.join(", ")}</p>
      <p className="meta">
        <span>{item.published}</span>
        <span> · {item.citation_count} citations</span>
        {item.citation_data_missing && (
          <span className="badge"> · citation data unavailable</span>
        )}
      </p>
      <p className="abstract">{item.abstract}</p>
    </article>
  );
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run from `frontend/`: `npm test`
Expected: ResultCard tests pass (4 passed in that file).

- [ ] **Step 5: Commit**

```bash
cd /Users/nehajohn/Desktop/research-buddy/.worktrees/milestone-1-discovery-ranking
git add frontend/src/components/ResultCard.tsx frontend/src/__tests__/ResultCard.test.tsx
git commit -m "refactor(frontend): ResultCard shows citations + date, no score breakdown"
```

---

## Task 9: SearchBar — controlled result-count selector

**Files:**
- Modify: `frontend/src/components/SearchBar.tsx`
- Modify: `frontend/src/__tests__/SearchBar.test.tsx`

The count selector is **controlled by the parent** (App owns `n`) so that changing it re-sorts the existing pool rather than only applying on the next search.

- [ ] **Step 1: Replace the contents of `frontend/src/__tests__/SearchBar.test.tsx`**

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { SearchBar } from "../components/SearchBar";

describe("SearchBar", () => {
  it("submits the typed query", async () => {
    const onSearch = vi.fn();
    render(<SearchBar onSearch={onSearch} loading={false} n={10} onNChange={vi.fn()} />);

    await userEvent.type(screen.getByLabelText(/query/i), "scaling laws");
    await userEvent.click(screen.getByRole("button", { name: /search/i }));

    expect(onSearch).toHaveBeenCalledWith("scaling laws");
  });

  it("calls onNChange when the count selector changes", async () => {
    const onNChange = vi.fn();
    render(<SearchBar onSearch={vi.fn()} loading={false} n={10} onNChange={onNChange} />);

    await userEvent.selectOptions(screen.getByLabelText(/results/i), "25");
    expect(onNChange).toHaveBeenCalledWith(25);
  });

  it("disables the button while loading", () => {
    render(<SearchBar onSearch={vi.fn()} loading={true} n={10} onNChange={vi.fn()} />);
    expect(screen.getByRole("button", { name: /search/i })).toBeDisabled();
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run from `frontend/`: `npm test`
Expected: FAIL — current `SearchBar` has an uncontrolled number input and `onSearch(query, n)` signature; new props `n`/`onNChange` and the select don't exist.

- [ ] **Step 3: Replace the contents of `frontend/src/components/SearchBar.tsx`**

```tsx
import { useState } from "react";

interface Props {
  onSearch: (query: string) => void;
  onNChange: (n: number) => void;
  n: number;
  loading: boolean;
}

const COUNT_OPTIONS = [5, 10, 25];

export function SearchBar({ onSearch, onNChange, n, loading }: Props) {
  const [query, setQuery] = useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (query.trim()) {
      onSearch(query.trim());
    }
  }

  return (
    <form className="search-bar" onSubmit={handleSubmit}>
      <label>
        Query
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="e.g. scaling laws"
        />
      </label>
      <label>
        Results
        <select value={n} onChange={(e) => onNChange(Number(e.target.value))}>
          {COUNT_OPTIONS.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      </label>
      <button type="submit" disabled={loading}>
        {loading ? "Searching…" : "Search"}
      </button>
    </form>
  );
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run from `frontend/`: `npm test`
Expected: SearchBar tests pass (3 passed in that file).

- [ ] **Step 5: Commit**

```bash
cd /Users/nehajohn/Desktop/research-buddy/.worktrees/milestone-1-discovery-ranking
git add frontend/src/components/SearchBar.tsx frontend/src/__tests__/SearchBar.test.tsx
git commit -m "refactor(frontend): SearchBar with controlled result-count selector"
```

---

## Task 10: SortControl — Citations/Recency toggle

**Files:**
- Create: `frontend/src/components/SortControl.tsx`
- Create: `frontend/src/__tests__/SortControl.test.tsx`

- [ ] **Step 1: Create the failing test `frontend/src/__tests__/SortControl.test.tsx`**

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { SortControl } from "../components/SortControl";

describe("SortControl", () => {
  it("renders Citations and Recency options", () => {
    render(<SortControl sort="relevance" onChange={vi.fn()} />);
    expect(screen.getByRole("button", { name: /citations/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /recency/i })).toBeInTheDocument();
  });

  it("calls onChange with the chosen sort key", async () => {
    const onChange = vi.fn();
    render(<SortControl sort="relevance" onChange={onChange} />);

    await userEvent.click(screen.getByRole("button", { name: /citations/i }));
    expect(onChange).toHaveBeenCalledWith("citations");

    await userEvent.click(screen.getByRole("button", { name: /recency/i }));
    expect(onChange).toHaveBeenCalledWith("recency");
  });

  it("marks the active sort as pressed", () => {
    render(<SortControl sort="citations" onChange={vi.fn()} />);
    expect(screen.getByRole("button", { name: /citations/i })).toHaveAttribute(
      "aria-pressed",
      "true"
    );
    expect(screen.getByRole("button", { name: /recency/i })).toHaveAttribute(
      "aria-pressed",
      "false"
    );
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run from `frontend/`: `npm test`
Expected: FAIL — cannot resolve `../components/SortControl`.

- [ ] **Step 3: Create `frontend/src/components/SortControl.tsx`**

```tsx
import type { SortKey } from "../types";

interface Props {
  sort: SortKey;
  onChange: (sort: SortKey) => void;
}

const OPTIONS: { key: SortKey; label: string }[] = [
  { key: "citations", label: "Citations" },
  { key: "recency", label: "Recency" },
];

export function SortControl({ sort, onChange }: Props) {
  return (
    <div className="sort-control" role="group" aria-label="Sort results">
      <span>Sort by:</span>
      {OPTIONS.map(({ key, label }) => (
        <button
          key={key}
          type="button"
          aria-pressed={sort === key}
          onClick={() => onChange(key)}
        >
          {label}
        </button>
      ))}
    </div>
  );
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run from `frontend/`: `npm test`
Expected: SortControl tests pass (3 passed in that file).

- [ ] **Step 5: Commit**

```bash
cd /Users/nehajohn/Desktop/research-buddy/.worktrees/milestone-1-discovery-ranking
git add frontend/src/components/SortControl.tsx frontend/src/__tests__/SortControl.test.tsx
git commit -m "feat(frontend): add SortControl (Citations/Recency toggle)"
```

---

## Task 11: App integration — search, sort, count, expired handling

**Files:**
- Modify: `frontend/src/App.tsx` (full replace)
- Modify: `frontend/src/__tests__/App.test.tsx` (full replace)

- [ ] **Step 1: Replace the contents of `frontend/src/__tests__/App.test.tsx`**

```tsx
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "../App";
import * as api from "../api";
import type { ResortResponse, SearchResponse, SearchResultItem } from "../types";

afterEach(() => {
  vi.restoreAllMocks();
});

function item(aid: string, title: string, citations: number): SearchResultItem {
  return {
    arxiv_id: aid,
    title,
    authors: ["A"],
    abstract: "abstract",
    published: "2020-01-23",
    url: `http://arxiv.org/abs/${aid}`,
    citation_count: citations,
    citation_data_missing: false,
  };
}

const searchResponse: SearchResponse = {
  search_id: "sid1",
  results: [item("a", "Alpha paper", 5), item("b", "Beta paper", 999)],
  pool_size: 200,
  warnings: [],
};

const citationsSorted: ResortResponse = {
  search_id: "sid1",
  results: [item("b", "Beta paper", 999), item("a", "Alpha paper", 5)],
  warnings: [],
};

describe("App", () => {
  it("renders results in relevance order after a search", async () => {
    vi.spyOn(api, "searchPapers").mockResolvedValue(searchResponse);
    render(<App />);

    await userEvent.type(screen.getByLabelText(/query/i), "scaling laws");
    await userEvent.click(screen.getByRole("button", { name: /search/i }));

    await waitFor(() => expect(screen.getByText(/Alpha paper/)).toBeInTheDocument());
  });

  it("re-sorts via the resort endpoint when Citations is clicked", async () => {
    vi.spyOn(api, "searchPapers").mockResolvedValue(searchResponse);
    const resortSpy = vi.spyOn(api, "resortPapers").mockResolvedValue(citationsSorted);
    render(<App />);

    await userEvent.type(screen.getByLabelText(/query/i), "scaling laws");
    await userEvent.click(screen.getByRole("button", { name: /search/i }));
    await waitFor(() => expect(screen.getByText(/Alpha paper/)).toBeInTheDocument());

    await userEvent.click(screen.getByRole("button", { name: /citations/i }));

    await waitFor(() => expect(resortSpy).toHaveBeenCalledWith("sid1", "citations", 10));
  });

  it("shows an error when the search fails", async () => {
    vi.spyOn(api, "searchPapers").mockRejectedValue(new Error("Search failed (503)"));
    render(<App />);

    await userEvent.type(screen.getByLabelText(/query/i), "x");
    await userEvent.click(screen.getByRole("button", { name: /search/i }));

    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent(/503/));
  });

  it("shows an expired message when re-sorting a lost search", async () => {
    vi.spyOn(api, "searchPapers").mockResolvedValue(searchResponse);
    vi.spyOn(api, "resortPapers").mockRejectedValue(
      new Error("Search expired — please search again.")
    );
    render(<App />);

    await userEvent.type(screen.getByLabelText(/query/i), "scaling laws");
    await userEvent.click(screen.getByRole("button", { name: /search/i }));
    await waitFor(() => expect(screen.getByText(/Alpha paper/)).toBeInTheDocument());

    await userEvent.click(screen.getByRole("button", { name: /recency/i }));
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent(/expired/i));
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run from `frontend/`: `npm test`
Expected: FAIL — current `App` imports `WeightSliders` and uses the old API; the sort toggle and resort wiring don't exist.

- [ ] **Step 3: Replace the contents of `frontend/src/App.tsx`**

```tsx
import { useState } from "react";
import { resortPapers, searchPapers } from "./api";
import { ResultList } from "./components/ResultList";
import { SearchBar } from "./components/SearchBar";
import { SortControl } from "./components/SortControl";
import type { SearchResultItem, SortKey } from "./types";
import "./App.css";

export default function App() {
  const [searchId, setSearchId] = useState<string | null>(null);
  const [results, setResults] = useState<SearchResultItem[]>([]);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [sort, setSort] = useState<SortKey>("relevance");
  const [n, setN] = useState(10);
  const [searched, setSearched] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSearch(query: string) {
    setLoading(true);
    setError(null);
    setSort("relevance");
    try {
      const resp = await searchPapers(query, n);
      setSearchId(resp.search_id);
      setResults(resp.results);
      setWarnings(resp.warnings);
      setSearched(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
      setResults([]);
      setSearched(true);
    } finally {
      setLoading(false);
    }
  }

  async function applySort(nextSort: SortKey, nextN: number) {
    if (!searchId) return;
    setError(null);
    try {
      const resp = await resortPapers(searchId, nextSort, nextN);
      setResults(resp.results);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    }
  }

  function handleSortChange(nextSort: SortKey) {
    setSort(nextSort);
    applySort(nextSort, n);
  }

  function handleNChange(nextN: number) {
    setN(nextN);
    applySort(sort, nextN);
  }

  return (
    <main className="app">
      <h1>Research Buddy</h1>
      <SearchBar onSearch={handleSearch} onNChange={handleNChange} n={n} loading={loading} />
      {searchId && <SortControl sort={sort} onChange={handleSortChange} />}

      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}

      {loading && <p className="loading">Searching…</p>}

      {!loading && searched && !error && (
        <ResultList results={results} warnings={warnings} />
      )}
    </main>
  );
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run from `frontend/`: `npm test`
Expected: App tests pass. (`WeightSliders` is no longer imported by `App`; it is deleted in Task 12.)

- [ ] **Step 5: Commit**

```bash
cd /Users/nehajohn/Desktop/research-buddy/.worktrees/milestone-1-discovery-ranking
git add frontend/src/App.tsx frontend/src/__tests__/App.test.tsx
git commit -m "feat(frontend): wire search + re-sort + count + expired handling in App"
```

---

## Task 12: Delete WeightSliders

**Files:**
- Delete: `frontend/src/components/WeightSliders.tsx`

- [ ] **Step 1: Confirm nothing imports WeightSliders**

Run from `frontend/`: `grep -rn "WeightSliders" src` (excluding the component file itself)
Expected: no matches other than `src/components/WeightSliders.tsx`. (App stopped importing it in Task 11.)

- [ ] **Step 2: Delete the file**

```bash
cd /Users/nehajohn/Desktop/research-buddy/.worktrees/milestone-1-discovery-ranking
git rm frontend/src/components/WeightSliders.tsx
```

- [ ] **Step 3: Run the full frontend suite and build**

Run from `frontend/`: `npm test` then `npm run build`
Expected: all tests pass; `npm run build` succeeds with no TypeScript errors (confirms no dangling references to removed types/components).

- [ ] **Step 4: Commit**

```bash
cd /Users/nehajohn/Desktop/research-buddy/.worktrees/milestone-1-discovery-ranking
git add frontend/src/components/WeightSliders.tsx
git commit -m "chore(frontend): remove obsolete WeightSliders component"
```

---

## Task 13: Documentation

**Files:**
- Modify: `CLAUDE.md`
- Modify: `README.md`

- [ ] **Step 1: Update the Architecture section in `CLAUDE.md`**

Replace the `Ranker` bullet (the line beginning "- **`Ranker`** — **pure function, no I/O.**") with:

```markdown
- **`Sorter`** — **pure function, no I/O.** `build_result_items()` combines arXiv candidates with citation counts (preserving arXiv/relevance order); `sort_papers(items, sort_key, n)` returns the top N by a single key (`relevance` = arXiv order, `citations`/`recency` = stable descending sort). No weighting.
```

- [ ] **Step 2: Update the `SearchService` bullet and load-bearing notes in `CLAUDE.md`**

Replace the `- **`SearchService`** — orchestrates arXiv → enrich → rank → return.` line with:

```markdown
- **`SearchService`** — orchestrates arXiv (fixed 200-candidate pool) → enrich all with citations → store the full pool under `search_id` → return relevance-order top N. A `resort(search_id, sort_key, n)` path re-sorts the stored pool with no new network calls.
```

Then replace the two-stage-sourcing load-bearing bullet (the line starting "- **Two-stage sourcing:**") with:

```markdown
- **Retrieve-then-sort:** arXiv finds a fixed pool of 200 candidates by relevance; the user then sorts that stored pool by citations or recency (top N, default 10). No weighted scoring. See `docs/superpowers/specs/2026-06-08-research-buddy-retrieve-then-sort-redesign.md`.
```

- [ ] **Step 3: Update the Commands section's frontend note and add the re-sort endpoint to `CLAUDE.md`**

Under `## Commands`, immediately after the `### Backend (`backend/`)` list, add:

```markdown
- API: `POST /api/search {query, n}` returns a `search_id` + relevance-ordered results; `GET /api/search/{search_id}?sort=citations|recency&n=10` re-sorts the stored pool.
```

- [ ] **Step 4: Update `README.md`**

Replace the opening paragraph of `README.md` (the lines starting "Milestone 1: paper discovery & ranking.") with:

```markdown
Milestone 1: paper discovery & ranking. A FastAPI backend retrieves the top 200
arXiv papers for a query (by relevance) and enriches them with OpenAlex citation
counts. The React frontend lets the user re-sort that pool by citations or
recency and shows the top N (default 10).

Citation enrichment uses OpenAlex (no API key required). Set the optional
`OPENALEX_MAILTO` env var to your email to use OpenAlex's faster "polite pool".
```

- [ ] **Step 5: Commit**

```bash
cd /Users/nehajohn/Desktop/research-buddy/.worktrees/milestone-1-discovery-ranking
git add CLAUDE.md README.md
git commit -m "docs: update CLAUDE.md and README for retrieve-then-sort model"
```

---

## Task 14: Full-stack verification

**Files:** none (verification only).

- [ ] **Step 1: Run both complete test suites**

```bash
cd /Users/nehajohn/Desktop/research-buddy/.worktrees/milestone-1-discovery-ranking
backend/.venv/bin/pytest backend -q
(cd frontend && npm test && npm run build)
```
Expected: backend all pass (live smoke skipped); frontend all pass; build clean.

- [ ] **Step 2: Launch both servers**

```bash
cd /Users/nehajohn/Desktop/research-buddy/.worktrees/milestone-1-discovery-ranking/backend
OPENALEX_MAILTO="nehaannajohn@gmail.com" .venv/bin/uvicorn app.main:app --port 8000 > /tmp/rb_be.log 2>&1 &
cd /Users/nehajohn/Desktop/research-buddy/.worktrees/milestone-1-discovery-ranking/frontend
npm run dev > /tmp/rb_fe.log 2>&1 &
sleep 4
curl -s http://127.0.0.1:8000/api/health
curl -s -o /dev/null -w "frontend %{http_code}\n" http://localhost:5173/
```
Expected: `{"status":"ok"}` and `frontend 200`.

- [ ] **Step 3: Manual check in the browser**

Open `http://localhost:5173`, search "scaling laws", confirm results render in relevance order, then click **Citations** and confirm the list reorders (most-cited first, "Scaling Laws for Neural Language Models" near the top) without a full reload, and **Recency** reorders by date. Change the result-count selector and confirm the list length changes via the re-sort endpoint.

- [ ] **Step 4: Stop the servers**

```bash
lsof -ti tcp:8000 | xargs kill -9 2>/dev/null; lsof -ti tcp:5173 | xargs kill -9 2>/dev/null; echo stopped
```

(No commit — verification only.)

---

## Final Verification Checklist

- [ ] **Backend:** `backend/.venv/bin/pytest backend -q` → all pass, live smoke skipped.
- [ ] **Frontend:** `(cd frontend && npm test && npm run build)` → all pass, build clean.
- [ ] **No dead references:** `grep -rn "Ranker\|Weights\|sub_scores\|final_score\|WeightSliders" backend/app frontend/src` → no matches in source (only in the superseded spec / git history).
- [ ] **End-to-end:** search → relevance order; Citations re-sort surfaces high-citation papers; Recency re-sort orders by date; result-count selector changes list length; unknown `search_id` → 404 / "search expired" in UI.

---

## Revision A — OpenAlex as single source (supersedes backend Tasks 1–5)

Per the spec amendment "OpenAlex as the single source", retrieval moves from arXiv
to OpenAlex. Backend Tasks 1–4 were implemented against arXiv and are now reworked
by tasks **RA1–RA4** below. **Frontend Tasks 6–12, plus docs (13) and verification
(14), are unchanged** — the `SearchResultItem` shape, the `Sorter.sort_papers`
function, the store, the `resort()` path, and both API endpoints all stay the same.

### RA1: OpenAlexClient (replaces ArxivClient + DOI CitationClient)
- Create `app/openalex_client.py`: `OpenAlexClient.search(query, pool_size) -> list[SearchResultItem]`, `OpenAlexUnavailable`, and `_reconstruct_abstract()`. GET `https://api.openalex.org/works` with `search=<query>`, `filter=primary_location.source.id:s4306400194`, `per-page=min(pool_size,200)`, the `select` list, optional `mailto`, `follow_redirects=True`; map each work → `SearchResultItem` (arxiv_id from DOI, url from `primary_location.landing_page_url`, authors from `authorships`, `date.fromisoformat(publication_date)`, `cited_by_count`, abstract reconstructed, `citation_data_missing=False`); skip works without an arXiv DOI; HTTP error → `OpenAlexUnavailable`.
- Create `tests/test_openalex_client.py` (mocked httpx, fixture JSON): request shape (search/filter/per-page/select), mailto present/absent, work→item mapping, abstract reconstruction, skip-non-arxiv, HTTP error → `OpenAlexUnavailable`.
- `git rm` `app/arxiv_client.py app/citation_client.py tests/test_arxiv_client.py tests/test_citation_client.py tests/fixtures/arxiv_sample.xml`.

### RA2: Models + Sorter cleanup
- `models.py`: remove `CandidatePaper` (now unused). Keep everything else. Update `tests/test_models.py` import (drop `CandidatePaper`).
- `sorter.py`: remove `build_result_items` (the client builds items now); keep `sort_papers`. Update `tests/test_sorter.py` to construct `SearchResultItem` directly via a local helper (no `CandidatePaper`/`build_result_items`).

### RA3: SearchService (single client)
- `search_service.py`: constructor becomes `(openalex_client, store)`. `search()` calls `openalex_client.search(request.query, POOL_SIZE)`, maps `OpenAlexUnavailable` → `SearchSourceUnavailable`, empty → "broaden" warning, stores full pool, returns relevance-order top n. `resort()` and `_store_and_respond()` unchanged. Remove the citation-degradation path. Rewrite `tests/test_search_service.py` with a `FakeOpenAlex` returning `list[SearchResultItem]`.

### RA4: main.py wiring + suite + live smoke
- `main.py`: `_service = SearchService(OpenAlexClient(mailto=os.getenv("OPENALEX_MAILTO")), _store)`. (API routes unchanged; `test_api.py` uses a `FakeService` and needs no change — confirm it still passes.)
- Replace `tests/test_live_smoke.py` with an OpenAlex retrieval smoke test (search "scaling laws" → returns results; top results include a highly-cited canonical paper). Remove the arXiv/Semantic-Scholar smoke tests.
- Run the full backend suite (live skipped) and confirm green.

`POOL_SIZE` stays 200.
