from __future__ import annotations

from datetime import date

from app.models import (
    CandidatePaper,
    SearchRequest,
    SearchResponse,
    SearchResultItem,
    SubScores,
    Weights,
)


def test_weights_defaults_match_spec():
    w = Weights()
    assert (w.relevance, w.citations, w.recency) == (0.5, 0.3, 0.2)


def test_search_request_rejects_empty_query():
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        SearchRequest(query="", n=5)


def test_search_request_rejects_non_positive_n():
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        SearchRequest(query="scaling laws", n=0)


def test_candidate_paper_roundtrip():
    c = CandidatePaper(
        arxiv_id="2301.12345",
        title="A Paper",
        authors=["Ada Lovelace"],
        abstract="abstract text",
        published=date(2023, 1, 15),
        url="http://arxiv.org/abs/2301.12345",
        relevance_rank=0,
    )
    assert c.relevance_rank == 0


def test_search_response_holds_results():
    item = SearchResultItem(
        arxiv_id="2301.12345",
        title="A Paper",
        authors=["Ada Lovelace"],
        abstract="abstract text",
        published=date(2023, 1, 15),
        url="http://arxiv.org/abs/2301.12345",
        citation_count=10,
        sub_scores=SubScores(relevance=1.0, citations=0.5, recency=0.8),
        final_score=0.81,
        citation_data_missing=False,
    )
    resp = SearchResponse(search_id="abc", results=[item], pool_size=50, warnings=[])
    assert resp.results[0].sub_scores.citations == 0.5
