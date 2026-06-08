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
def test_semantic_scholar_returns_counts_for_real_ids():
    papers = ArxivClient().search("attention is all you need", pool_size=5)
    counts = CitationClient().get_citation_counts([p.arxiv_id for p in papers])
    assert isinstance(counts, dict)
