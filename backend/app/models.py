from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class Weights(BaseModel):
    relevance: float = 0.5
    citations: float = 0.3
    recency: float = 0.2


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    n: int = Field(ge=1, le=100)
    weights: Optional[Weights] = None


class CandidatePaper(BaseModel):
    arxiv_id: str
    title: str
    authors: list[str]
    abstract: str
    published: date
    url: str
    relevance_rank: int  # 0-based; 0 = most relevant


class SubScores(BaseModel):
    relevance: float
    citations: float
    recency: float


class SearchResultItem(BaseModel):
    arxiv_id: str
    title: str
    authors: list[str]
    abstract: str
    published: date
    url: str
    citation_count: int
    sub_scores: SubScores
    final_score: float
    citation_data_missing: bool


class SearchResponse(BaseModel):
    search_id: str
    results: list[SearchResultItem]
    pool_size: int
    warnings: list[str]
