from __future__ import annotations

import pytest

from app.openalex_client import OpenAlexClient


@pytest.mark.live
def test_openalex_returns_arxiv_results_for_real_query():
    items = OpenAlexClient(mailto="nehaannajohn@gmail.com").search("scaling laws", 25)
    assert len(items) > 0
    assert all(i.arxiv_id for i in items)
    # a heavily-cited canonical paper should be in the top results
    assert any(i.citation_count > 100 for i in items)


@pytest.mark.live
def test_openalex_ranks_canonical_scaling_laws_paper_in_top_results():
    items = OpenAlexClient(mailto="nehaannajohn@gmail.com").search("scaling laws", 25)
    ids = [i.arxiv_id for i in items]
    # "Scaling Laws for Neural Language Models" is ranked #1 by OpenAlex relevance
    assert "2001.08361" in ids
