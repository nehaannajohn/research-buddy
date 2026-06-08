from __future__ import annotations

import pytest

from app.arxiv_client import ArxivClient
from app.citation_client import CitationClient, CitationUnavailable


@pytest.mark.live
def test_arxiv_returns_candidates_for_real_query():
    papers = ArxivClient().search("scaling laws", pool_size=10)
    assert len(papers) > 0
    assert papers[0].arxiv_id
    assert papers[0].title


@pytest.mark.live
def test_semantic_scholar_returns_counts_for_real_ids():
    papers = ArxivClient().search("attention is all you need", pool_size=5)
    try:
        counts = CitationClient().get_citation_counts([p.arxiv_id for p in papers])
    except CitationUnavailable as exc:
        # Unauthenticated Semantic Scholar rate-limits aggressively (HTTP 429).
        # That is a transient infra condition, not a code regression — and it is
        # exactly the failure SearchService degrades around — so skip rather than
        # fail the smoke test when it happens.
        if "429" in str(exc):
            pytest.skip("Semantic Scholar rate-limited (429)")
        raise
    assert isinstance(counts, dict)
