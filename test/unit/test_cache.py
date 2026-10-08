"""
Unit tests — utils/cache.py

Kesh Redis ustida ishlaydi. Testlar `conftest.fake_redis` (fakeredis)
orqali ketadi, shuning uchun get_cache/set_cache mock qilinmaydi —
haqiqiy kod yo'li, haqiqiy JSON serializatsiya bilan tekshiriladi.

Bu fayl avval xotiradagi `_store` lug'atini sinagan edi. Kesh Redis'ga
ko'chirilganda `_store` yo'qolgan, ammo testlar yangilanmagan.
"""
from unittest.mock import patch

import pytest
import redis as redis_lib

from utils.cache import (
    get_cache,
    get_cached_dashboard,
    invalidate_cache,
    invalidate_dashboard_cache,
    invalidate_prefix,
    set_cache,
    set_cached_dashboard,
)


# ─── get_cache / set_cache ────────────────────────────────────────────────────

class TestGetSetCache:
    def test_set_then_get(self):
        set_cache("key1", {"x": 1}, ttl=60)
        assert get_cache("key1") == {"x": 1}

    def test_missing_key_returns_none(self):
        assert get_cache("nonexistent") is None

    def test_set_cache_applies_ttl(self, redis_conn):
        set_cache("ttlkey", "value", ttl=90)
        # setex ishlatilgani uchun TTL o'rnatilgan bo'lishi kerak
        assert 0 < redis_conn.ttl("ttlkey") <= 90

    def test_default_ttl_is_60(self, redis_conn):
        set_cache("defttl", "value")
        assert 0 < redis_conn.ttl("defttl") <= 60

    def test_expired_key_returns_none(self, redis_conn):
        set_cache("expkey", "value", ttl=60)
        # TTL tugaganini Redis darajasida simulyatsiya qilamiz
        redis_conn.delete("expkey")
        assert get_cache("expkey") is None

    def test_string_value(self):
        set_cache("str", "hello", ttl=60)
        assert get_cache("str") == "hello"

    def test_list_value(self):
        set_cache("lst", [1, 2, 3], ttl=60)
        assert get_cache("lst") == [1, 2, 3]

    def test_int_value(self):
        set_cache("num", 42, ttl=60)
        assert get_cache("num") == 42

    def test_bool_value(self):
        set_cache("flag", True, ttl=60)
        assert get_cache("flag") is True

    def test_nested_structure_roundtrips(self):
        data = {"a": [1, {"b": "c"}], "d": None}
        set_cache("nested", data, ttl=60)
        assert get_cache("nested") == data

    def test_none_data_is_indistinguishable_from_miss(self):
        # json.dumps(None) == "null" — saqlanadi, lekin o'qishda None qaytadi,
        # ya'ni kesh miss bilan farqlanmaydi. Bu dizayn xususiyati.
        set_cache("nullkey", None, ttl=60)
        assert get_cache("nullkey") is None

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

    def test_stored_as_json(self, redis_conn):
        set_cache("rawcheck", {"k": "v"}, ttl=60)
        assert redis_conn.get("rawcheck") == '{"k": "v"}'

    def test_unicode_value_roundtrips(self):
        set_cache("uz", {"name": "Ko'chat o'simligi"}, ttl=60)
        assert get_cache("uz") == {"name": "Ko'chat o'simligi"}


# ─── Xatolik yo'llari — Redis ishlamay qolganda ─────────────────────────────
# Kesh qatlami hech qachon so'rovni yiqitmasligi kerak: Redis o'chgan bo'lsa
# kesh miss sifatida davom etadi.

class TestRedisFailureHandling:
    def test_get_cache_returns_none_on_connection_error(self):
        with patch("utils.cache.redis_client.get",
                   side_effect=redis_lib.ConnectionError("down")):
            assert get_cache("anykey") is None

    def test_get_cache_returns_none_on_invalid_json(self, redis_conn):
        redis_conn.set("badjson", "{not valid json")
        assert get_cache("badjson") is None

    def test_set_cache_swallows_connection_error(self):
        with patch("utils.cache.redis_client.setex",
                   side_effect=redis_lib.ConnectionError("down")):
            set_cache("k", "v", ttl=60)  # ko'tarilmasligi kerak

    def test_set_cache_swallows_unserializable_value(self):
        # json.dumps bo'lmaydigan obyekt — xato chiqmasligi kerak
        set_cache("unser", object(), ttl=60)
        assert get_cache("unser") is None

    def test_invalidate_cache_swallows_connection_error(self):
        with patch("utils.cache.redis_client.delete",
                   side_effect=redis_lib.ConnectionError("down")):
            invalidate_cache("k")  # ko'tarilmasligi kerak

    def test_invalidate_prefix_swallows_connection_error(self):
        with patch("utils.cache.redis_client.scan",
                   side_effect=redis_lib.ConnectionError("down")):
            invalidate_prefix("p_")  # ko'tarilmasligi kerak


# ─── invalidate_cache ─────────────────────────────────────────────────────────

class TestInvalidateCache:
    def test_invalidate_existing(self):
        set_cache("del1", "x", ttl=60)
        invalidate_cache("del1")
        assert get_cache("del1") is None

    def test_invalidate_nonexistent_no_error(self):
        invalidate_cache("does_not_exist")

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

    def test_prefix_is_a_prefix_not_exact_match(self):
        set_cache("abc", "x", ttl=60)
        set_cache("abcd", "y", ttl=60)
        invalidate_prefix("abc")
        assert get_cache("abc") is None
        assert get_cache("abcd") is None  # "abcd" ham "abc*" ga mos keladi

    def test_scans_past_first_page(self, redis_conn):
        # SCAN count=100 — bitta sahifadan ko'p kalit bo'lsa ham hammasi
        # o'chishi kerak (cursor loop to'g'ri aylanadi).
        for i in range(250):
            set_cache(f"bulk_{i}", i, ttl=60)
        invalidate_prefix("bulk_")
        assert redis_conn.keys("bulk_*") == []


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

    def test_dashboard_key_format(self, redis_conn):
        set_cached_dashboard(777, {"x": 1})
        assert redis_conn.exists("dashboard_777")

    def test_dashboard_ttl_is_60(self, redis_conn):
        set_cached_dashboard(5, {"x": 1})
        assert 0 < redis_conn.ttl("dashboard_5") <= 60
