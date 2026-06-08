from __future__ import annotations

import os

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.arxiv_client import ArxivClient
from app.citation_client import CitationClient
from app.models import SearchRequest, SearchResponse
from app.search_service import SearchService, SearchSourceUnavailable
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
