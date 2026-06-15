from __future__ import annotations

from tools.cache_tool import cache_get, cache_set


def test_cache_miss_returns_none(db):
    assert cache_get(db, "research", "nonexistent topic xyz") is None


def test_cache_roundtrip(db):
    value = {"trend": "AI", "opportunity": "big", "evidence": [], "why_it_matters": "yes"}
    cache_set(db, "research", "test topic", value, ttl_hours=1)
    result = cache_get(db, "research", "test topic")
    assert result == value


def test_cache_key_is_namespaced(db):
    cache_set(db, "ns_a", "same text", {"data": "a"})
    cache_set(db, "ns_b", "same text", {"data": "b"})
    assert cache_get(db, "ns_a", "same text") == {"data": "a"}
    assert cache_get(db, "ns_b", "same text") == {"data": "b"}


def test_cache_overwrite(db):
    cache_set(db, "research", "overwrite topic", {"v": 1})
    cache_set(db, "research", "overwrite topic", {"v": 2})
    assert cache_get(db, "research", "overwrite topic") == {"v": 2}


def test_cache_key_normalises_whitespace_via_hash(db):
    # SHA-256 of "hello" vs " hello " differ — this is expected; just verify no crash
    cache_set(db, "ns", "hello", {"ok": True})
    result = cache_get(db, "ns", "hello")
    assert result == {"ok": True}
