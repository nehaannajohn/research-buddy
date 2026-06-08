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
