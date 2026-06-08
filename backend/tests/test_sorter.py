from __future__ import annotations

from datetime import date

from app.models import SearchResultItem, SortKey
from app.sorter import sort_papers


def _item(aid, citations=0, published=date(2020, 1, 1)):
    return SearchResultItem(
        arxiv_id=aid,
        title=f"T{aid}",
        authors=["A"],
        abstract="x",
        published=published,
        url=f"http://arxiv.org/abs/{aid}",
        citation_count=citations,
        citation_data_missing=False,
    )


def test_sort_relevance_is_identity():
    items = [_item("a"), _item("b"), _item("c")]
    assert [i.arxiv_id for i in sort_papers(items, SortKey.relevance, 3)] == ["a", "b", "c"]


def test_sort_citations_descending():
    items = [_item("a", 5), _item("b", 100), _item("c", 20)]
    assert [i.arxiv_id for i in sort_papers(items, SortKey.citations, 3)] == ["b", "c", "a"]


def test_sort_recency_descending():
    items = [
        _item("old", published=date(2018, 1, 1)),
        _item("new", published=date(2024, 1, 1)),
        _item("mid", published=date(2021, 1, 1)),
    ]
    assert [i.arxiv_id for i in sort_papers(items, SortKey.recency, 3)] == ["new", "mid", "old"]


def test_sort_is_stable_on_ties_preserving_input_order():
    items = [_item("a", 0), _item("b", 0), _item("c", 0)]
    assert [i.arxiv_id for i in sort_papers(items, SortKey.citations, 3)] == ["a", "b", "c"]


def test_sort_truncates_to_n():
    items = [_item(str(i)) for i in range(5)]
    assert [i.arxiv_id for i in sort_papers(items, SortKey.relevance, 2)] == ["0", "1"]


def test_sort_n_larger_than_pool_returns_all():
    items = [_item("a", 1), _item("b", 2)]
    assert len(sort_papers(items, SortKey.citations, 10)) == 2


def test_sort_empty_pool_returns_empty():
    assert sort_papers([], SortKey.citations, 10) == []
