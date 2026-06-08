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
