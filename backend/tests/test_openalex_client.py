from __future__ import annotations

from datetime import date

import httpx
import pytest

from app.openalex_client import OpenAlexClient, OpenAlexUnavailable, _reconstruct_abstract

ARXIV_SOURCE_ID = "s4306400194"


def _work(
    doi="https://doi.org/10.48550/arxiv.2001.08361",
    title="Scaling Laws for Neural Language Models",
    cited=1504,
    pubdate="2020-01-23",
    inv=None,
    landing="http://arxiv.org/abs/2001.08361",
    authors=("Jared Kaplan", "Sam McCandlish"),
):
    return {
        "doi": doi,
        "title": title,
        "authorships": [{"author": {"display_name": a}} for a in authors],
        "publication_date": pubdate,
        "cited_by_count": cited,
        "abstract_inverted_index": inv
        if inv is not None
        else {"We": [0], "study": [1], "scaling": [2], "laws": [3]},
        "primary_location": {"landing_page_url": landing},
    }


def _ok(results, url="https://api.openalex.org/works"):
    return httpx.Response(200, json={"results": results}, request=httpx.Request("GET", url))


def test_reconstruct_abstract_orders_words():
    inv = {"Neural": [0], "scaling": [1], "laws": [2]}
    assert _reconstruct_abstract(inv) == "Neural scaling laws"


def test_reconstruct_abstract_empty():
    assert _reconstruct_abstract(None) == ""
    assert _reconstruct_abstract({}) == ""


def test_search_builds_request(monkeypatch):
    captured = {}

    def fake_get(url, params, timeout, follow_redirects):
        captured["url"] = url
        captured["params"] = params
        return _ok([_work()], url)

    monkeypatch.setattr(httpx, "get", fake_get)
    OpenAlexClient(mailto="dev@example.com").search("scaling laws", 200)
    p = captured["params"]
    assert p["search"] == "scaling laws"
    assert p["filter"] == f"primary_location.source.id:{ARXIV_SOURCE_ID}"
    assert p["per-page"] == 200
    assert "cited_by_count" in p["select"] and "abstract_inverted_index" in p["select"]
    assert p["mailto"] == "dev@example.com"


def test_search_caps_per_page_at_200_and_omits_mailto(monkeypatch):
    captured = {}

    def fake_get(url, params, timeout, follow_redirects):
        captured["params"] = params
        return _ok([], url)

    monkeypatch.setattr(httpx, "get", fake_get)
    OpenAlexClient().search("q", 500)
    assert captured["params"]["per-page"] == 200
    assert "mailto" not in captured["params"]


def test_search_maps_work_to_result_item(monkeypatch):
    monkeypatch.setattr(
        httpx, "get", lambda url, params, timeout, follow_redirects: _ok([_work()], url)
    )
    items = OpenAlexClient().search("scaling laws", 200)
    assert len(items) == 1
    it = items[0]
    assert it.arxiv_id == "2001.08361"
    assert it.title == "Scaling Laws for Neural Language Models"
    assert it.authors == ["Jared Kaplan", "Sam McCandlish"]
    assert it.published == date(2020, 1, 23)
    assert it.url == "http://arxiv.org/abs/2001.08361"
    assert it.citation_count == 1504
    assert it.citation_data_missing is False
    assert "scaling" in it.abstract


def test_search_skips_works_without_arxiv_doi(monkeypatch):
    works = [_work(), _work(doi="https://doi.org/10.1145/other", title="Not arXiv")]
    monkeypatch.setattr(
        httpx, "get", lambda url, params, timeout, follow_redirects: _ok(works, url)
    )
    items = OpenAlexClient().search("q", 200)
    assert [i.arxiv_id for i in items] == ["2001.08361"]


def test_http_error_raises_openalex_unavailable(monkeypatch):
    def boom(url, params, timeout, follow_redirects):
        raise httpx.ConnectError("down")

    monkeypatch.setattr(httpx, "get", boom)
    with pytest.raises(OpenAlexUnavailable):
        OpenAlexClient().search("q", 200)
