from __future__ import annotations

import pytest

from app.arxiv_client import ArxivClient
from app.citation_client import CitationClient


@pytest.mark.live
def test_arxiv_returns_candidates_for_real_query():
    papers = ArxivClient().search("scaling laws", pool_size=10)
    assert len(papers) > 0
    assert papers[0].arxiv_id
    assert papers[0].title


@pytest.mark.live
def test_openalex_returns_citation_count_for_known_arxiv_id():
    # "Scaling Laws for Neural Language Models" (arXiv:2001.08361) is heavily
    # cited and indexed in OpenAlex, so this is deterministic, not flaky.
    counts = CitationClient().get_citation_counts(["2001.08361"])
    assert counts.get("2001.08361", 0) > 0
