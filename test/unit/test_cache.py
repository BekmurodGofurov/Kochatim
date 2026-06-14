"""
Unit tests — utils/cache.py
In-process dict keshi funksiyalari testlanadi.
"""
import time

import pytest

from utils.cache import (
    get_cache,
    get_cached_dashboard,
    invalidate_cache,
    invalidate_dashboard_cache,
    invalidate_prefix,
    set_cache,
    set_cached_dashboard,
)
import utils.cache as cache_module


@pytest.fixture(autouse=True)
def reset_store():
    cache_module._store.clear()
    yield
    cache_module._store.clear()


# ─── get_cache / set_cache ────────────────────────────────────────────────────

class TestGetSetCache:
    def test_set_then_get(self):
        set_cache("key1", {"x": 1}, ttl=60)
        assert get_cache("key1") == {"x": 1}

    def test_missing_key_returns_none(self):
        assert get_cache("nonexistent") is None

    def test_expired_returns_none(self):
        set_cache("expkey", "value", ttl=1)
        # TTL=1 soniya — hoziroq yaratilgan, lekin vaqtni sun'iy o'tkazib yuborish
        entry = cache_module._store["expkey"]
        entry["time"] = time.time() - 2  # 2 soniya oldin yaratilgandek qilib qo'yamiz
        assert get_cache("expkey") is None

    def test_expired_key_cleaned_from_store(self):
        set_cache("cleankey", "data", ttl=1)
        cache_module._store["cleankey"]["time"] = time.time() - 2
        get_cache("cleankey")
        assert "cleankey" not in cache_module._store

    def test_string_value(self):
        set_cache("str", "hello", ttl=60)
        assert get_cache("str") == "hello"

    def test_list_value(self):
        set_cache("lst", [1, 2, 3], ttl=60)
        assert get_cache("lst") == [1, 2, 3]

    def test_none_data_is_stored_and_retrievable(self):
        set_cache("nullkey", None, ttl=60)
        # None data ham saqlanishi kerak
        result = get_cache("nullkey")
        assert result is None  # lekin key mavjud
        # Aslida None qaytarayotgani kesh miss bilan farqlanmaydi — bu dizayn xususiyati

    def test_overwrite_existing_key(self):
        set_cache("ow", "first", ttl=60)
        set_cache("ow", "second", ttl=60)
        assert get_cache("ow") == "second"

    def test_not_expired_within_ttl(self):
        set_cache("fresh", "data", ttl=3600)
        assert get_cache("fresh") == "data"

    def test_multiple_keys_independent(self):
        set_cache("a", 1, ttl=60)
        set_cache("b", 2, ttl=60)
        assert get_cache("a") == 1
        assert get_cache("b") == 2


# ─── invalidate_cache ─────────────────────────────────────────────────────────

class TestInvalidateCache:
    def test_invalidate_existing(self):
        set_cache("del1", "x", ttl=60)
        invalidate_cache("del1")
        assert get_cache("del1") is None

    def test_invalidate_nonexistent_no_error(self):
        invalidate_cache("does_not_exist")  # xato bo'lmasligi kerak

    def test_invalidate_one_leaves_others(self):
        set_cache("keep", "yes", ttl=60)
        set_cache("remove", "no", ttl=60)
        invalidate_cache("remove")
        assert get_cache("keep") == "yes"
        assert get_cache("remove") is None


# ─── invalidate_prefix ───────────────────────────────────────────────────────

class TestInvalidatePrefix:
    def test_removes_matching_prefix(self):
        set_cache("session_abc", 1, ttl=60)
        set_cache("session_def", 2, ttl=60)
        set_cache("other_key", 3, ttl=60)
        invalidate_prefix("session_")
        assert get_cache("session_abc") is None
        assert get_cache("session_def") is None
        assert get_cache("other_key") == 3

    def test_nonexistent_prefix_no_error(self):
        invalidate_prefix("no_such_prefix_")

    def test_exact_match_prefix(self):
        set_cache("abc", "x", ttl=60)
        set_cache("abcd", "y", ttl=60)
        invalidate_prefix("abc")
        assert get_cache("abc") is None
        assert get_cache("abcd") is None  # "abcd" ham "abc" prefiksi bilan boshlanadi


# ─── Dashboard cache wrappers ─────────────────────────────────────────────────

class TestDashboardCache:
    def test_set_and_get_dashboard(self):
        data = {"user": {"u_id": 1}, "categories": []}
        set_cached_dashboard(1, data)
        assert get_cached_dashboard(1) == data

    def test_get_dashboard_miss(self):
        assert get_cached_dashboard(99999) is None

    def test_invalidate_dashboard(self):
        set_cached_dashboard(2, {"test": True})
        invalidate_dashboard_cache(2)
        assert get_cached_dashboard(2) is None

    def test_different_users_isolated(self):
        set_cached_dashboard(10, {"user": "ten"})
        set_cached_dashboard(20, {"user": "twenty"})
        invalidate_dashboard_cache(10)
        assert get_cached_dashboard(10) is None
        assert get_cached_dashboard(20) == {"user": "twenty"}
