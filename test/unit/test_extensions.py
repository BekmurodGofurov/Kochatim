"""
Unit tests — backend/extensions.py

Postgres connection pool. `_pool` modul darajasidagi global, shuning
uchun har test oldidan None ga qaytariladi — aks holda testlar bir-biriga
ta'sir qiladi va tartibga bog'liq bo'lib qoladi.
"""
from unittest.mock import MagicMock, patch

import pytest

import extensions
from extensions import get_conn, get_pool, init_pool, put_conn


@pytest.fixture(autouse=True)
def reset_pool():
    original = extensions._pool
    extensions._pool = None
    yield
    extensions._pool = original


@pytest.fixture
def fake_pool_cls():
    """ThreadedConnectionPool klassini mock qiladi."""
    with patch("extensions.ThreadedConnectionPool") as cls:
        cls.return_value = MagicMock()
        yield cls


# ─── init_pool ────────────────────────────────────────────────────────────────

class TestInitPool:
    def test_creates_pool(self, fake_pool_cls):
        init_pool()
        fake_pool_cls.assert_called_once()
        assert extensions._pool is fake_pool_cls.return_value

    def test_uses_configured_sizes_and_dsn(self, fake_pool_cls):
        init_pool()
        kwargs = fake_pool_cls.call_args.kwargs
        assert kwargs["minconn"] == 1   # conftest DB_POOL_MIN=1
        assert kwargs["maxconn"] == 5   # conftest DB_POOL_MAX=5
        assert kwargs["dsn"].startswith("postgresql://")

    def test_is_idempotent(self, fake_pool_cls):
        """
        Ikkinchi chaqiruv yangi pool yaratmaydi. app.py create_app() ni
        modul darajasida ham, fixture ichida ham chaqiradi — aks holda
        har chaqiruv yangi ulanishlar to'plamini ochib yuborardi.
        """
        init_pool()
        init_pool()
        fake_pool_cls.assert_called_once()

    def test_propagates_connection_failure(self, fake_pool_cls):
        fake_pool_cls.side_effect = Exception("could not connect")
        with pytest.raises(Exception, match="could not connect"):
            init_pool()


# ─── get_pool ─────────────────────────────────────────────────────────────────

class TestGetPool:
    def test_initialises_lazily_when_unset(self, fake_pool_cls):
        assert extensions._pool is None
        assert get_pool() is fake_pool_cls.return_value
        fake_pool_cls.assert_called_once()

    def test_returns_existing_pool_without_recreating(self, fake_pool_cls):
        init_pool()
        fake_pool_cls.reset_mock()
        assert get_pool() is fake_pool_cls.return_value
        fake_pool_cls.assert_not_called()


# ─── get_conn ─────────────────────────────────────────────────────────────────

class TestGetConn:
    def test_takes_connection_from_pool(self, fake_pool_cls):
        pool = fake_pool_cls.return_value
        pool.getconn.return_value = "conn-1"
        assert get_conn() == "conn-1"
        pool.getconn.assert_called_once()

    def test_initialises_pool_if_needed(self, fake_pool_cls):
        get_conn()
        fake_pool_cls.assert_called_once()

    def test_propagates_pool_exhaustion(self, fake_pool_cls):
        pool = fake_pool_cls.return_value
        pool.getconn.side_effect = Exception("connection pool exhausted")
        with pytest.raises(Exception, match="exhausted"):
            get_conn()


# ─── put_conn ─────────────────────────────────────────────────────────────────

class TestPutConn:
    def test_returns_connection_for_reuse_by_default(self, fake_pool_cls):
        pool = fake_pool_cls.return_value
        conn = MagicMock()
        put_conn(conn)
        pool.putconn.assert_called_once_with(conn, close=False)

    def test_close_true_discards_connection(self, fake_pool_cls):
        """
        db.py uzilgan ulanishni close=True bilan qaytaradi. Bu pool
        uni yopib tashlashi uchun yagona yo'l — conn.close() pooldan
        olingan ulanish uchun yetarli emas.
        """
        pool = fake_pool_cls.return_value
        conn = MagicMock()
        put_conn(conn, close=True)
        pool.putconn.assert_called_once_with(conn, close=True)

    def test_initialises_pool_if_needed(self, fake_pool_cls):
        put_conn(MagicMock())
        fake_pool_cls.assert_called_once()
