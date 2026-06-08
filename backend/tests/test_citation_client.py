from __future__ import annotations

import httpx
import pytest

from app.citation_client import CitationClient, CitationUnavailable


def _ok(results, url="https://api.openalex.org/works"):
    return httpx.Response(200, json={"results": results}, request=httpx.Request("GET", url))


def test_empty_input_returns_empty_dict_without_calling(monkeypatch):
    def fail(*a, **k):
        raise AssertionError("should not be called")

    monkeypatch.setattr(httpx, "get", fail)
    assert CitationClient().get_citation_counts([]) == {}


def test_maps_arxiv_doi_results_to_bare_ids(monkeypatch):
    captured = {}

    def fake_get(url, params, timeout, follow_redirects):
        captured["url"] = url
        captured["params"] = params
        results = [
            {"doi": "https://doi.org/10.48550/arxiv.2001.08361", "cited_by_count": 1504},
            {"doi": "https://doi.org/10.48550/arxiv.2001.11111", "cited_by_count": 12},
        ]
        return _ok(results, url)

    monkeypatch.setattr(httpx, "get", fake_get)
    counts = CitationClient().get_citation_counts(["2001.08361", "2001.11111", "1810.04805"])

    assert captured["params"]["filter"] == (
        "doi:10.48550/arxiv.2001.08361|10.48550/arxiv.2001.11111|10.48550/arxiv.1810.04805"
    )
    assert captured["params"]["select"] == "doi,cited_by_count"
    # 1810.04805 not returned by OpenAlex (deduped upstream) -> omitted, treated as missing
    assert counts == {"2001.08361": 1504, "2001.11111": 12}


def test_includes_mailto_when_configured(monkeypatch):
    captured = {}

    def fake_get(url, params, timeout, follow_redirects):
        captured["params"] = params
        return _ok([], url)

    monkeypatch.setattr(httpx, "get", fake_get)
    CitationClient(mailto="dev@example.com").get_citation_counts(["2001.08361"])
    assert captured["params"]["mailto"] == "dev@example.com"


def test_omits_mailto_when_not_configured(monkeypatch):
    captured = {}

    def fake_get(url, params, timeout, follow_redirects):
        captured["params"] = params
        return _ok([], url)

    monkeypatch.setattr(httpx, "get", fake_get)
    CitationClient().get_citation_counts(["2001.08361"])
    assert "mailto" not in captured["params"]


def test_chunks_requests_in_batches_of_50(monkeypatch):
    calls = []

    def fake_get(url, params, timeout, follow_redirects):
        calls.append(params["filter"])
        return _ok([], url)

    monkeypatch.setattr(httpx, "get", fake_get)
    ids = [f"2101.{i:05d}" for i in range(120)]  # 120 ids -> chunks of 50, 50, 20
    CitationClient().get_citation_counts(ids)

    assert len(calls) == 3
    assert calls[0].count("|") == 49  # 50 DOIs -> 49 separators
    assert calls[1].count("|") == 49
    assert calls[2].count("|") == 19  # last chunk has 20 DOIs


def test_skips_results_with_null_citation_count(monkeypatch):
    def fake_get(url, params, timeout, follow_redirects):
        results = [
            {"doi": "https://doi.org/10.48550/arxiv.2001.08361", "cited_by_count": None},
            {"doi": "https://doi.org/10.48550/arxiv.2001.11111", "cited_by_count": 7},
        ]
        return _ok(results, url)

    monkeypatch.setattr(httpx, "get", fake_get)
    counts = CitationClient().get_citation_counts(["2001.08361", "2001.11111"])
    assert counts == {"2001.11111": 7}


def test_http_error_raises_citation_unavailable(monkeypatch):
    def fake_get(url, params, timeout, follow_redirects):
        raise httpx.ConnectError("boom")

    monkeypatch.setattr(httpx, "get", fake_get)
    with pytest.raises(CitationUnavailable):
        CitationClient().get_citation_counts(["2001.08361"])
