from __future__ import annotations

import os

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.arxiv_abstracts import ArxivAbstractClient
from app.openalex_client import OpenAlexClient
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
    OpenAlexClient(mailto=os.getenv("OPENALEX_MAILTO")),
    ArxivAbstractClient(),
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
