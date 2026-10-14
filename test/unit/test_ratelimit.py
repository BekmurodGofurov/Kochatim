"""
Unit tests — utils/ratelimit.py and utils.cache.claim_once

Fixed-window counters and the single-use claim behind the replay protection.
Both signal "Redis is unreachable" with None so the caller can choose.
"""
from unittest.mock import patch

import pytest
import redis as redis_lib

from utils import ratelimit
from utils.cache import claim_once


class TestRateLimit:
    def test_count_starts_at_zero(self):
        assert ratelimit.count("s", "1.2.3.4", 600) == 0

    def test_record_increments_and_returns_the_new_total(self):
        assert [ratelimit.record("s", "1.2.3.4", 600) for _ in range(3)] == [1, 2, 3]
        assert ratelimit.count("s", "1.2.3.4", 600) == 3

    def test_counting_does_not_change_the_counter(self):
        ratelimit.record("s", "x", 600)
        for _ in range(5):
            ratelimit.count("s", "x", 600)
        assert ratelimit.count("s", "x", 600) == 1

    def test_scopes_and_identities_are_independent(self):
        ratelimit.record("a", "ip1", 600)
        assert ratelimit.count("b", "ip1", 600) == 0
        assert ratelimit.count("a", "ip2", 600) == 0

    def test_the_counter_expires(self, redis_conn):
        ratelimit.record("s", "x", 600)
        keys = redis_conn.keys("rl:s:x:*")
        assert len(keys) == 1 and 0 < redis_conn.ttl(keys[0]) <= 600

    def test_a_new_window_starts_from_zero(self):
        with patch("utils.ratelimit.time.time", return_value=1_000_000):
            ratelimit.record("s", "x", 600)
            assert ratelimit.count("s", "x", 600) == 1
        with patch("utils.ratelimit.time.time", return_value=1_000_000 + 600):
            assert ratelimit.count("s", "x", 600) == 0

    def test_retry_after_is_time_left_in_the_window(self):
        with patch("utils.ratelimit.time.time", return_value=1_000_000 + 100):
            assert ratelimit.retry_after(600) == 600 - ((1_000_000 + 100) % 600)
        with patch("utils.ratelimit.time.time", return_value=1_200_000):  # exactly on a boundary
            assert ratelimit.retry_after(600) == 600

    def test_hostile_identifiers_stay_inside_their_key(self, redis_conn):
        ratelimit.record("s", "1.2.3.4\r\nFLUSHALL", 600)
        assert redis_conn.keys("rl:*")

    def test_redis_down_on_count_returns_none(self):
        with patch("utils.cache.redis_client.get", side_effect=redis_lib.ConnectionError("down")):
            assert ratelimit.count("s", "x", 600) is None

    def test_redis_down_on_record_returns_none(self):
        with patch("utils.cache.redis_client.pipeline", side_effect=redis_lib.ConnectionError("down")):
            assert ratelimit.record("s", "x", 600) is None


class TestClaimOnce:
    def test_first_claim_wins_the_second_loses(self):
        assert claim_once("proof:abc", 120) is True
        assert claim_once("proof:abc", 120) is False

    def test_different_keys_do_not_collide(self):
        assert claim_once("proof:a", 120) is True
        assert claim_once("proof:b", 120) is True

    def test_claim_expires(self, redis_conn):
        claim_once("proof:abc", 120)
        assert 0 < redis_conn.ttl("proof:abc") <= 120

    def test_a_claim_can_be_made_again_after_it_expires(self, redis_conn):
        claim_once("proof:abc", 120)
        redis_conn.delete("proof:abc")  # what TTL expiry does
        assert claim_once("proof:abc", 120) is True

    def test_redis_down_returns_none_not_true_or_false(self):
        with patch("utils.cache.redis_client.set", side_effect=redis_lib.ConnectionError("down")):
            assert claim_once("proof:abc", 120) is None
