from __future__ import annotations

import httpx
import pytest

from app.citation_client import CitationClient, CitationUnavailable


def test_empty_input_returns_empty_dict_without_calling(monkeypatch):
    def fail(*a, **k):
        raise AssertionError("should not be called")

    monkeypatch.setattr(httpx, "post", fail)
    assert CitationClient().get_citation_counts([]) == {}


def test_maps_resolved_ids_and_skips_nulls(monkeypatch):
    captured = {}

    def fake_post(url, params, json, timeout):
        captured["params"] = params
        captured["json"] = json
        body = [{"citationCount": 42}, None, {"citationCount": 0}]
        return httpx.Response(200, json=body, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "post", fake_post)
    counts = CitationClient().get_citation_counts(["aaa", "bbb", "ccc"])

    assert captured["params"]["fields"] == "citationCount"
    assert captured["json"]["ids"] == ["ARXIV:aaa", "ARXIV:bbb", "ARXIV:ccc"]
    assert counts == {"aaa": 42, "ccc": 0}  # bbb unmatched -> omitted


def test_http_error_raises_citation_unavailable(monkeypatch):
    def fake_post(url, params, json, timeout):
        raise httpx.ConnectError("rate limited")

    monkeypatch.setattr(httpx, "post", fake_post)
    with pytest.raises(CitationUnavailable):
        CitationClient().get_citation_counts(["aaa"])
