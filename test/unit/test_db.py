"""
Unit tests — backend/db.py

Bu modulning qiyin joyi — ulanish uzilganda bir marta qayta urinish:
`execute`/`fetch_*` xato retryable bo'lsa, ulanishni poolga QAYTA
ISHLATMASLIK uchun close=True bilan qaytaradi va so'rovni takrorlaydi.

Testlar haqiqiy Postgres'siz, pool darajasida mock bilan ishlaydi.
`get_conn`/`put_conn` db modulining o'z nomsohasida patch qilinadi,
chunki db.py ularni `from extensions import ...` orqali qiymat bo'yicha
bog'lab olgan.
"""
from unittest.mock import MagicMock, call, patch

import psycopg2
import pytest

from db import (
    _dict_from_cursor,
    _discard_conn,
    _is_retryable_db_error,
    execute,
    execute_returning,
    fetch_all,
    fetch_one,
)


def make_conn(rows=None, one_row=None, description=None, execute_side_effect=None):
    """Kursori oldindan sozlangan fake ulanish."""
    cur = MagicMock()
    cur.description = description or [("a",), ("b",)]
    cur.fetchone.return_value = one_row
    cur.fetchall.return_value = rows
    if execute_side_effect is not None:
        cur.execute.side_effect = execute_side_effect
    conn = MagicMock()
    conn.cursor.return_value = cur
    return conn, cur


@pytest.fixture
def pool():
    """get_conn/put_conn ni mock qiladi va ikkisini ham qaytaradi."""
    with patch("db.get_conn") as get_conn, patch("db.put_conn") as put_conn:
        yield get_conn, put_conn


# ─── _dict_from_cursor ────────────────────────────────────────────────────────

class TestDictFromCursor:
    def test_maps_columns_to_values(self):
        cur = MagicMock()
        cur.description = [("u_id",), ("u_name",)]
        assert _dict_from_cursor(cur, (1, "Ali")) == {"u_id": 1, "u_name": "Ali"}

    def test_single_column(self):
        cur = MagicMock()
        cur.description = [("count",)]
        assert _dict_from_cursor(cur, (7,)) == {"count": 7}

    def test_preserves_none_values(self):
        cur = MagicMock()
        cur.description = [("a",), ("b",)]
        assert _dict_from_cursor(cur, (None, 2)) == {"a": None, "b": 2}

    def test_uses_first_element_of_description_tuples(self):
        # psycopg2 description 7 elementli tuple beradi — faqat nom olinadi
        cur = MagicMock()
        cur.description = [("u_id", 20, None, 8, None, None, None)]
        assert _dict_from_cursor(cur, (42,)) == {"u_id": 42}

    def test_maps_every_column_in_description(self):
        cur = MagicMock()
        cur.description = [("a",), ("b",), ("c",)]
        assert _dict_from_cursor(cur, (1, 2, 3)) == {"a": 1, "b": 2, "c": 3}

    def test_row_shorter_than_description_raises(self):
        """
        Funksiya `range(len(cols))` bo'yicha yuradi, shuning uchun qatorda
        ustundan kam qiymat bo'lsa IndexError beradi. psycopg2 har doim
        teng uzunlik qaytargani uchun amalda bu holat yuz bermaydi —
        test mavjud xatti-harakatni qayd etadi.
        """
        cur = MagicMock()
        cur.description = [("a",), ("b",), ("c",)]
        with pytest.raises(IndexError):
            _dict_from_cursor(cur, (1, 2))


# ─── _is_retryable_db_error ───────────────────────────────────────────────────

class TestIsRetryableDbError:
    @pytest.mark.parametrize("msg", [
        "SSL connection has been closed unexpectedly",
        "server closed the connection unexpectedly",
        "connection already closed",
        "terminating connection due to administrator command",
    ])
    def test_known_transient_messages_are_retryable(self, msg):
        assert _is_retryable_db_error(Exception(msg)) is True

    def test_message_match_is_case_insensitive(self):
        assert _is_retryable_db_error(Exception("CONNECTION ALREADY CLOSED")) is True

    def test_operational_error_is_retryable(self):
        assert _is_retryable_db_error(psycopg2.OperationalError("boom")) is True

    def test_interface_error_is_retryable(self):
        assert _is_retryable_db_error(psycopg2.InterfaceError("boom")) is True

    def test_programming_error_is_not_retryable(self):
        # Sintaksis xatosini qayta urinish ma'nosiz
        assert _is_retryable_db_error(psycopg2.ProgrammingError("syntax error")) is False

    def test_integrity_error_is_not_retryable(self):
        assert _is_retryable_db_error(psycopg2.IntegrityError("duplicate key")) is False

    def test_plain_exception_is_not_retryable(self):
        assert _is_retryable_db_error(ValueError("nope")) is False


# ─── _discard_conn ────────────────────────────────────────────────────────────

class TestDiscardConn:
    def test_returns_connection_to_pool_closed(self):
        conn = MagicMock()
        with patch("db.put_conn") as put_conn:
            _discard_conn(conn)
        put_conn.assert_called_once_with(conn, close=True)

    def test_falls_back_to_conn_close_when_pool_raises(self):
        conn = MagicMock()
        with patch("db.put_conn", side_effect=Exception("pool gone")):
            _discard_conn(conn)
        conn.close.assert_called_once()

    def test_swallows_error_from_fallback_close(self):
        conn = MagicMock()
        conn.close.side_effect = Exception("already dead")
        with patch("db.put_conn", side_effect=Exception("pool gone")):
            _discard_conn(conn)  # ko'tarilmasligi kerak


# ─── execute ──────────────────────────────────────────────────────────────────

class TestExecute:
    def test_commits_and_returns_none(self, pool):
        get_conn, put_conn = pool
        conn, cur = make_conn()
        get_conn.return_value = conn

        assert execute("UPDATE t SET x=1") is None
        cur.execute.assert_called_once_with("UPDATE t SET x=1", ())
        conn.commit.assert_called_once()

    def test_passes_params(self, pool):
        get_conn, _ = pool
        conn, cur = make_conn()
        get_conn.return_value = conn

        execute("UPDATE t SET x=%s", (5,))
        cur.execute.assert_called_once_with("UPDATE t SET x=%s", (5,))

    def test_closes_cursor_and_returns_connection(self, pool):
        get_conn, put_conn = pool
        conn, cur = make_conn()
        get_conn.return_value = conn

        execute("SELECT 1")
        cur.close.assert_called_once()
        put_conn.assert_called_once_with(conn)

    def test_retries_once_on_retryable_error(self, pool):
        get_conn, put_conn = pool
        dead, dead_cur = make_conn(
            execute_side_effect=psycopg2.OperationalError("server closed the connection")
        )
        fresh, fresh_cur = make_conn()
        get_conn.side_effect = [dead, fresh]

        with patch("db._discard_conn") as discard:
            execute("UPDATE t SET x=1")

        discard.assert_called_once_with(dead)
        fresh_cur.execute.assert_called_once()
        fresh.commit.assert_called_once()

    def test_does_not_retry_twice(self, pool):
        """Ikkinchi urinish ham yiqilsa xato ko'tariladi — cheksiz tsikl yo'q."""
        get_conn, _ = pool
        err = psycopg2.OperationalError("server closed the connection")
        first, _ = make_conn(execute_side_effect=err)
        second, _ = make_conn(execute_side_effect=err)
        get_conn.side_effect = [first, second]

        with patch("db._discard_conn"), pytest.raises(psycopg2.OperationalError):
            execute("UPDATE t SET x=1")
        assert get_conn.call_count == 2

    def test_non_retryable_error_raises_immediately(self, pool):
        get_conn, put_conn = pool
        conn, _ = make_conn(
            execute_side_effect=psycopg2.ProgrammingError("syntax error")
        )
        get_conn.return_value = conn

        with pytest.raises(psycopg2.ProgrammingError):
            execute("SELEKT 1")
        assert get_conn.call_count == 1
        put_conn.assert_called_once_with(conn)

    def test_cursor_close_error_does_not_mask_result(self, pool):
        get_conn, _ = pool
        conn, cur = make_conn()
        cur.close.side_effect = Exception("cursor already closed")
        get_conn.return_value = conn

        assert execute("UPDATE t SET x=1") is None


# ─── execute_returning ───────────────────────────────────────────────────────

class TestExecuteReturning:
    def test_returns_row_as_dict(self, pool):
        get_conn, _ = pool
        conn, _cur = make_conn(one_row=(1, "Olma"),
                               description=[("t_id",), ("t_name",)])
        get_conn.return_value = conn

        assert execute_returning("INSERT ... RETURNING t_id, t_name") == {
            "t_id": 1, "t_name": "Olma"
        }

    def test_commits(self, pool):
        get_conn, _ = pool
        conn, _ = make_conn(one_row=(1,), description=[("t_id",)])
        get_conn.return_value = conn

        execute_returning("INSERT ... RETURNING t_id")
        conn.commit.assert_called_once()

    def test_returns_none_when_nothing_returned(self, pool):
        get_conn, _ = pool
        conn, _ = make_conn(one_row=None)
        get_conn.return_value = conn

        assert execute_returning("INSERT ... RETURNING t_id") is None

    def test_retries_once_on_retryable_error(self, pool):
        get_conn, _ = pool
        dead, _ = make_conn(
            execute_side_effect=psycopg2.InterfaceError("connection already closed")
        )
        fresh, _ = make_conn(one_row=(9,), description=[("t_id",)])
        get_conn.side_effect = [dead, fresh]

        with patch("db._discard_conn"):
            assert execute_returning("INSERT ... RETURNING t_id") == {"t_id": 9}

    def test_non_retryable_error_raises(self, pool):
        get_conn, _ = pool
        conn, _ = make_conn(
            execute_side_effect=psycopg2.IntegrityError("duplicate key")
        )
        get_conn.return_value = conn

        with pytest.raises(psycopg2.IntegrityError):
            execute_returning("INSERT ... RETURNING t_id")


# ─── fetch_one ────────────────────────────────────────────────────────────────

class TestFetchOne:
    def test_returns_row_as_dict(self, pool):
        get_conn, _ = pool
        conn, _ = make_conn(one_row=(123, "Ali"),
                            description=[("u_id",), ("u_name",)])
        get_conn.return_value = conn

        assert fetch_one("SELECT u_id, u_name FROM users") == {
            "u_id": 123, "u_name": "Ali"
        }

    def test_returns_none_when_no_row(self, pool):
        get_conn, _ = pool
        conn, _ = make_conn(one_row=None)
        get_conn.return_value = conn

        assert fetch_one("SELECT 1 WHERE false") is None

    def test_does_not_commit(self, pool):
        """O'qish tranzaksiyani yopmaydi — pool connectionni qayta ishlatadi."""
        get_conn, _ = pool
        conn, _ = make_conn(one_row=(1,), description=[("x",)])
        get_conn.return_value = conn

        fetch_one("SELECT 1")
        conn.commit.assert_not_called()

    def test_returns_connection_to_pool(self, pool):
        get_conn, put_conn = pool
        conn, _ = make_conn(one_row=(1,), description=[("x",)])
        get_conn.return_value = conn

        fetch_one("SELECT 1")
        put_conn.assert_called_once_with(conn)

    def test_retries_once_on_retryable_error(self, pool):
        get_conn, _ = pool
        dead, _ = make_conn(
            execute_side_effect=Exception("SSL connection has been closed unexpectedly")
        )
        fresh, _ = make_conn(one_row=(5,), description=[("u_id",)])
        get_conn.side_effect = [dead, fresh]

        with patch("db._discard_conn"):
            assert fetch_one("SELECT u_id FROM users") == {"u_id": 5}

    def test_non_retryable_error_raises(self, pool):
        get_conn, _ = pool
        conn, _ = make_conn(execute_side_effect=ValueError("bad params"))
        get_conn.return_value = conn

        with pytest.raises(ValueError):
            fetch_one("SELECT 1")


# ─── fetch_all ────────────────────────────────────────────────────────────────

class TestFetchAll:
    def test_returns_list_of_dicts(self, pool):
        get_conn, _ = pool
        conn, _ = make_conn(rows=[(1, "a"), (2, "b")],
                            description=[("c_id",), ("c_name",)])
        get_conn.return_value = conn

        assert fetch_all("SELECT c_id, c_name FROM categories") == [
            {"c_id": 1, "c_name": "a"},
            {"c_id": 2, "c_name": "b"},
        ]

    def test_empty_result_returns_empty_list(self, pool):
        get_conn, _ = pool
        conn, _ = make_conn(rows=[])
        get_conn.return_value = conn

        assert fetch_all("SELECT 1 WHERE false") == []

    def test_none_from_fetchall_returns_empty_list(self, pool):
        """`cur.fetchall() or []` — None hollarida ham ro'yxat qaytadi."""
        get_conn, _ = pool
        conn, _ = make_conn(rows=None)
        get_conn.return_value = conn

        assert fetch_all("SELECT 1") == []

    def test_does_not_commit(self, pool):
        get_conn, _ = pool
        conn, _ = make_conn(rows=[])
        get_conn.return_value = conn

        fetch_all("SELECT 1")
        conn.commit.assert_not_called()

    def test_retries_once_on_retryable_error(self, pool):
        get_conn, _ = pool
        dead, _ = make_conn(
            execute_side_effect=Exception("terminating connection")
        )
        fresh, _ = make_conn(rows=[(1,)], description=[("x",)])
        get_conn.side_effect = [dead, fresh]

        with patch("db._discard_conn"):
            assert fetch_all("SELECT x FROM t") == [{"x": 1}]

    def test_single_row(self, pool):
        get_conn, _ = pool
        conn, _ = make_conn(rows=[(42,)], description=[("n",)])
        get_conn.return_value = conn

        assert fetch_all("SELECT n FROM t") == [{"n": 42}]


# ─── Qayta urinish semantikasi — umumiy qoida ────────────────────────────────

class TestRetrySemantics:
    @pytest.mark.parametrize("fn,kwargs", [
        (execute, {}),
        (execute_returning, {}),
        (fetch_one, {}),
        (fetch_all, {}),
    ])
    def test_discarded_connection_is_never_reused(self, pool, fn, kwargs):
        """
        MUHIM: uzilgan ulanish poolga close=True bilan qaytariladi.
        Oddiy put_conn bilan qaytsa, o'lik socket keyingi so'rovga beriladi.
        """
        get_conn, put_conn = pool
        dead, _ = make_conn(
            execute_side_effect=psycopg2.OperationalError("server closed the connection")
        )
        fresh, _ = make_conn(rows=[], one_row=None, description=[("x",)])
        get_conn.side_effect = [dead, fresh]

        with patch("db._discard_conn") as discard:
            fn("SELECT 1", **kwargs)

        discard.assert_called_once_with(dead)
        # O'lik ulanish oddiy put_conn orqali qaytmagan bo'lishi kerak
        assert call(dead) not in put_conn.call_args_list
