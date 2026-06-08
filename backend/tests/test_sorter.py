from __future__ import annotations

from datetime import date

from app.models import CandidatePaper, SortKey
from app.sorter import build_result_items, sort_papers


def _candidate(aid, rank_pos, published=date(2020, 1, 1)):
    return CandidatePaper(
        arxiv_id=aid,
        title=f"T{aid}",
        authors=["A"],
        abstract="x",
        published=published,
        url=f"http://arxiv.org/abs/{aid}",
        relevance_rank=rank_pos,
    )


def test_build_result_items_preserves_order_and_flags_missing():
    cands = [_candidate("a", 0), _candidate("b", 1)]
    items = build_result_items(cands, {"a": 5})
    assert [i.arxiv_id for i in items] == ["a", "b"]  # arXiv order preserved
    assert items[0].citation_count == 5 and items[0].citation_data_missing is False
    assert items[1].citation_count == 0 and items[1].citation_data_missing is True


def test_sort_relevance_is_identity():
    cands = [_candidate("a", 0), _candidate("b", 1), _candidate("c", 2)]
    items = build_result_items(cands, {})
    out = sort_papers(items, SortKey.relevance, n=3)
    assert [i.arxiv_id for i in out] == ["a", "b", "c"]


def test_sort_citations_descending():
    cands = [_candidate("a", 0), _candidate("b", 1), _candidate("c", 2)]
    items = build_result_items(cands, {"a": 5, "b": 100, "c": 20})
    out = sort_papers(items, SortKey.citations, n=3)
    assert [i.arxiv_id for i in out] == ["b", "c", "a"]


def test_sort_recency_descending():
    cands = [
        _candidate("old", 0, published=date(2018, 1, 1)),
        _candidate("new", 1, published=date(2024, 1, 1)),
        _candidate("mid", 2, published=date(2021, 1, 1)),
    ]
    items = build_result_items(cands, {})
    out = sort_papers(items, SortKey.recency, n=3)
    assert [i.arxiv_id for i in out] == ["new", "mid", "old"]


def test_sort_is_stable_on_ties_preserving_relevance_order():
    cands = [_candidate("a", 0), _candidate("b", 1), _candidate("c", 2)]
    items = build_result_items(cands, {"a": 0, "b": 0, "c": 0})
    out = sort_papers(items, SortKey.citations, n=3)
    assert [i.arxiv_id for i in out] == ["a", "b", "c"]


def test_sort_truncates_to_n():
    cands = [_candidate(str(i), i) for i in range(5)]
    items = build_result_items(cands, {})
    out = sort_papers(items, SortKey.relevance, n=2)
    assert [i.arxiv_id for i in out] == ["0", "1"]


def test_sort_n_larger_than_pool_returns_all():
    cands = [_candidate("a", 0), _candidate("b", 1)]
    items = build_result_items(cands, {})
    out = sort_papers(items, SortKey.citations, n=10)
    assert len(out) == 2


def test_sort_empty_pool_returns_empty():
    assert sort_papers([], SortKey.citations, n=10) == []
