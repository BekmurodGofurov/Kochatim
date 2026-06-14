"""
Unit tests — utils/time.py
"""
from datetime import datetime, timedelta, timezone

import pytest

from utils.time import naive_utc, utc_in_seconds, utcnow, utcnow_plus_seconds


class TestUtcnow:
    def test_returns_datetime(self):
        assert isinstance(utcnow(), datetime)

    def test_has_timezone(self):
        dt = utcnow()
        assert dt.tzinfo is not None

    def test_is_utc(self):
        dt = utcnow()
        assert dt.utcoffset().total_seconds() == 0

    def test_recent_time(self):
        before = datetime.now(timezone.utc) - timedelta(seconds=1)
        result = utcnow()
        after = datetime.now(timezone.utc) + timedelta(seconds=1)
        assert before <= result <= after


class TestUtcnowPlusSeconds:
    def test_adds_positive_seconds(self):
        before = utcnow()
        result = utcnow_plus_seconds(3600)
        assert result > before
        diff = (result - before).total_seconds()
        assert 3599 <= diff <= 3601

    def test_adds_zero_seconds(self):
        before = utcnow()
        result = utcnow_plus_seconds(0)
        after = utcnow()
        assert before <= result <= after

    def test_adds_large_seconds(self):
        result = utcnow_plus_seconds(30 * 24 * 3600)  # 30 kun
        now = utcnow()
        diff_days = (result - now).days
        assert 29 <= diff_days <= 30

    def test_has_timezone(self):
        assert utcnow_plus_seconds(60).tzinfo is not None


class TestUtcInSeconds:
    def test_same_as_utcnow_plus_seconds(self):
        t1 = utc_in_seconds(100)
        t2 = utcnow_plus_seconds(100)
        diff = abs((t1 - t2).total_seconds())
        assert diff < 1

    def test_returns_datetime(self):
        assert isinstance(utc_in_seconds(60), datetime)

    def test_future_time(self):
        result = utc_in_seconds(120)
        assert result > utcnow()


class TestNaiveUtc:
    def test_removes_tzinfo(self):
        aware = datetime.now(timezone.utc)
        naive = naive_utc(aware)
        assert naive.tzinfo is None

    def test_preserves_time_values(self):
        aware = datetime(2026, 6, 13, 12, 30, 0, tzinfo=timezone.utc)
        naive = naive_utc(aware)
        assert naive.year == 2026
        assert naive.month == 6
        assert naive.day == 13
        assert naive.hour == 12
        assert naive.minute == 30

    def test_converts_other_timezone_to_utc(self):
        from datetime import timezone as tz
        plus5 = tz(timedelta(hours=5))
        aware = datetime(2026, 6, 13, 17, 0, 0, tzinfo=plus5)
        naive = naive_utc(aware)
        # UTC+5 da 17:00 == UTC da 12:00
        assert naive.hour == 12
        assert naive.tzinfo is None

    def test_roundtrip(self):
        original = utcnow()
        naive = naive_utc(original)
        assert naive.tzinfo is None
        assert abs((naive - original.replace(tzinfo=None)).total_seconds()) < 1
