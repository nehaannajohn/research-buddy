from __future__ import annotations

from datetime import date
from pathlib import Path

import httpx
import pytest

from app.arxiv_client import ArxivClient, ArxivUnavailable

FIXTURE = Path(__file__).parent / "fixtures" / "arxiv_sample.xml"


def test_parse_extracts_metadata_and_rank():
    raw = FIXTURE.read_text()
    papers = ArxivClient._parse(raw)
    assert len(papers) == 2

    first = papers[0]
    assert first.arxiv_id == "2001.11111"
    assert first.title == "Scaling Laws for Neural Language Models"
    assert first.authors == ["Jane Researcher", "John Scientist"]
    assert first.published == date(2020, 1, 23)
    assert first.relevance_rank == 0
    assert first.url == "http://arxiv.org/abs/2001.11111v2"


def test_parse_handles_legacy_identifier_and_strips_version():
    raw = FIXTURE.read_text()
    papers = ArxivClient._parse(raw)
    assert papers[1].arxiv_id == "cond-mat/0211034"
    assert papers[1].relevance_rank == 1


def test_search_builds_relevance_sorted_request(monkeypatch):
    captured = {}

    def fake_get(url, params, timeout):
        captured["url"] = url
        captured["params"] = params
        return httpx.Response(
            200,
            text=FIXTURE.read_text(),
            request=httpx.Request("GET", url, params=params),
        )

    monkeypatch.setattr(httpx, "get", fake_get)
    client = ArxivClient()
    papers = client.search("scaling laws", pool_size=50)

    assert captured["params"]["search_query"] == "all:scaling laws"
    assert captured["params"]["sortBy"] == "relevance"
    assert captured["params"]["max_results"] == 50
    assert len(papers) == 2


def test_search_retries_once_then_raises(monkeypatch):
    calls = {"n": 0}

    def always_fail(url, params, timeout):
        calls["n"] += 1
        raise httpx.ConnectError("boom")

    monkeypatch.setattr(httpx, "get", always_fail)
    monkeypatch.setattr("app.arxiv_client.time.sleep", lambda _s: None)

    client = ArxivClient()
    with pytest.raises(ArxivUnavailable):
        client.search("x", pool_size=10)
    assert calls["n"] == 2  # initial attempt + one retry
