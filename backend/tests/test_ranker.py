from __future__ import annotations

import math
from datetime import date

from app.models import CandidatePaper, Weights
from app.ranker import rank


def _candidate(arxiv_id, rank_pos, published=date(2023, 1, 1)):
    return CandidatePaper(
        arxiv_id=arxiv_id,
        title=f"Paper {arxiv_id}",
        authors=["A"],
        abstract="x",
        published=published,
        url=f"http://arxiv.org/abs/{arxiv_id}",
        relevance_rank=rank_pos,
    )


def test_single_candidate_gets_relevance_one():
    cands = [_candidate("1", 0)]
    out = rank(cands, {"1": 0}, Weights(), n=5)
    assert out[0].sub_scores.relevance == 1.0


def test_relevance_scales_linearly_by_rank():
    cands = [_candidate("a", 0), _candidate("b", 1), _candidate("c", 2)]
    out = {r.arxiv_id: r.sub_scores.relevance for r in rank(cands, {}, Weights(), n=3)}
    assert out["a"] == 1.0
    assert out["b"] == 0.5
    assert out["c"] == 0.0


def test_citations_are_log_scaled_then_normalized():
    cands = [_candidate("a", 0), _candidate("b", 1)]
    counts = {"a": 999, "b": 9}  # log1p(999)=6.908..., log1p(9)=2.303...
    out = {r.arxiv_id: r.sub_scores.citations for r in rank(cands, counts, Weights(), n=2)}
    assert out["a"] == 1.0
    assert math.isclose(out["b"], math.log1p(9) / math.log1p(999), rel_tol=1e-9)


def test_all_zero_citations_gives_zero_citation_scores():
    cands = [_candidate("a", 0), _candidate("b", 1)]
    out = {r.arxiv_id: r.sub_scores.citations for r in rank(cands, {"a": 0, "b": 0}, Weights(), n=2)}
    assert out["a"] == 0.0 and out["b"] == 0.0


def test_recency_normalized_across_date_range():
    cands = [
        _candidate("old", 0, published=date(2020, 1, 1)),
        _candidate("mid", 1, published=date(2021, 1, 1)),
        _candidate("new", 2, published=date(2022, 1, 1)),
    ]
    out = {r.arxiv_id: r.sub_scores.recency for r in rank(cands, {}, Weights(), n=3)}
    assert out["new"] == 1.0
    assert out["old"] == 0.0
    assert 0.0 < out["mid"] < 1.0


def test_identical_dates_give_recency_one():
    cands = [_candidate("a", 0), _candidate("b", 1)]
    out = {r.arxiv_id: r.sub_scores.recency for r in rank(cands, {}, Weights(), n=2)}
    assert out["a"] == 1.0 and out["b"] == 1.0


def test_final_score_applies_weights():
    cands = [_candidate("a", 0, published=date(2022, 1, 1))]
    out = rank(cands, {"a": 0}, Weights(relevance=0.5, citations=0.3, recency=0.2), n=1)[0]
    # single candidate: rel=1.0, cit=0.0 (count 0), rec=1.0 -> 0.5*1 + 0.3*0 + 0.2*1 = 0.7
    assert math.isclose(out.final_score, 0.7, rel_tol=1e-9)


def test_returns_top_n_sorted_descending():
    cands = [_candidate("a", 0), _candidate("b", 1), _candidate("c", 2)]
    # citations dominate ordering with heavy weight
    counts = {"a": 1, "b": 1000, "c": 10}
    out = rank(cands, counts, Weights(relevance=0.0, citations=1.0, recency=0.0), n=2)
    assert [r.arxiv_id for r in out] == ["b", "c"]
    assert len(out) == 2


def test_missing_citation_data_is_flagged_and_counts_zero():
    cands = [_candidate("a", 0), _candidate("b", 1)]
    out = {r.arxiv_id: r for r in rank(cands, {"a": 5}, Weights(), n=2)}
    assert out["a"].citation_data_missing is False
    assert out["b"].citation_data_missing is True
    assert out["b"].citation_count == 0


def test_empty_citation_map_degrades_to_relevance_recency_ordering():
    cands = [
        _candidate("a", 0, published=date(2020, 1, 1)),
        _candidate("b", 1, published=date(2022, 1, 1)),
    ]
    out = rank(cands, {}, Weights(), n=2)
    # all citation sub-scores 0, ordering by 0.5*rel + 0.2*rec
    # a: 0.5*1.0 + 0.2*0.0 = 0.5 ; b: 0.5*0.0 + 0.2*1.0 = 0.2
    assert [r.arxiv_id for r in out] == ["a", "b"]
    assert all(r.citation_data_missing for r in out)
