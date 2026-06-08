from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from app.arxiv_abstracts import ArxivAbstractClient, ArxivAbstractsUnavailable

FIXTURE = Path(__file__).parent / "fixtures" / "arxiv_abstracts_sample.xml"


def _ok(text, url="https://export.arxiv.org/api/query", params=None):
    return httpx.Response(200, text=text, request=httpx.Request("GET", url, params=params or {}))


def test_empty_input_returns_empty_without_calling(monkeypatch):
    def fail(*a, **k):
        raise AssertionError("should not be called")

    monkeypatch.setattr(httpx, "get", fail)
    assert ArxivAbstractClient().get_abstracts([]) == {}


def test_maps_id_to_abstract_stripping_version_and_whitespace(monkeypatch):
    captured = {}

    def fake_get(url, params, timeout, follow_redirects):
        captured["url"] = url
        captured["params"] = params
        captured["follow_redirects"] = follow_redirects
        return _ok(FIXTURE.read_text(), url, params)

    monkeypatch.setattr(httpx, "get", fake_get)
    out = ArxivAbstractClient().get_abstracts(["2001.08361", "1507.07878"])

    assert captured["url"].startswith("https://")
    assert captured["follow_redirects"] is True
    assert captured["params"]["id_list"] == "2001.08361,1507.07878"
    assert out["2001.08361"].startswith("We study empirical scaling laws")
    assert "  " not in out["2001.08361"]  # whitespace normalized
    assert out["1507.07878"].startswith("Scaling laws are powerful")


def test_chunks_requests_in_batches_of_100(monkeypatch):
    calls = []

    def fake_get(url, params, timeout, follow_redirects):
        calls.append(params["id_list"])
        return _ok("<feed xmlns='http://www.w3.org/2005/Atom'></feed>", url, params)

    monkeypatch.setattr(httpx, "get", fake_get)
    ids = [f"2101.{i:05d}" for i in range(250)]  # 250 -> 100, 100, 50
    ArxivAbstractClient().get_abstracts(ids)

    assert len(calls) == 3
    assert calls[0].count(",") == 99
    assert calls[2].count(",") == 49


def test_http_error_raises_unavailable(monkeypatch):
    def boom(url, params, timeout, follow_redirects):
        raise httpx.ConnectError("down")

    monkeypatch.setattr(httpx, "get", boom)
    with pytest.raises(ArxivAbstractsUnavailable):
        ArxivAbstractClient().get_abstracts(["2001.08361"])
