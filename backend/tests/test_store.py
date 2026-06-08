from __future__ import annotations

from app.store import ResultStore


def test_save_and_get_roundtrip():
    store = ResultStore()
    store.save("abc", ["item1", "item2"])
    assert store.get("abc") == ["item1", "item2"]


def test_get_unknown_id_returns_none():
    assert ResultStore().get("missing") is None
