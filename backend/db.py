from contextlib import contextmanager
from typing import Optional, Any, Dict, List, Tuple
import psycopg2

from extensions import get_conn, put_conn


def _dict_from_cursor(cur, row) -> Dict[str, Any]:
    cols = [d[0] for d in cur.description]
    return {cols[i]: row[i] for i in range(len(cols))}


def _is_retryable_db_error(e: Exception) -> bool:
    msg = str(e).lower()
    return (
        "ssl connection has been closed unexpectedly" in msg
        or "server closed the connection unexpectedly" in msg
        or "connection already closed" in msg
        or "terminating connection" in msg
        or isinstance(e, psycopg2.OperationalError)
        or isinstance(e, psycopg2.InterfaceError)
    )


def _discard_conn(conn):
    """
    MUHIM: conn pooldan olingan, shuning uchun conn.close() yetarli emas.
    Poolga close=True bilan qaytaramiz.
    """
    try:
        put_conn(conn, close=True)
    except Exception:
        try:
            conn.close()
        except Exception:
            pass


def execute(query: str, params: Tuple[Any, ...] = ()) -> None:
    for attempt in (1, 2):
        conn = None
        cur = None
        try:
            conn = get_conn()
            cur = conn.cursor()
            cur.execute(query, params)
            conn.commit()
            return
        except Exception as e:
            if conn is not None and _is_retryable_db_error(e) and attempt == 1:
                _discard_conn(conn)
                conn = None
                continue
            raise
        finally:
            if cur is not None:
                try:
                    cur.close()
                except Exception:
                    pass
            if conn is not None:
                put_conn(conn)


def execute_returning(query: str, params: Tuple[Any, ...] = ()) -> Optional[Dict[str, Any]]:
    for attempt in (1, 2):
        conn = None
        cur = None
        try:
            conn = get_conn()
            cur = conn.cursor()
            cur.execute(query, params)
            row = cur.fetchone()
            conn.commit()
            if not row:
                return None
            return _dict_from_cursor(cur, row)
        except Exception as e:
            if conn is not None and _is_retryable_db_error(e) and attempt == 1:
                _discard_conn(conn)
                conn = None
                continue
            raise
        finally:
            if cur is not None:
                try:
                    cur.close()
                except Exception:
                    pass
            if conn is not None:
                put_conn(conn)


def fetch_one(query: str, params: Tuple[Any, ...] = ()) -> Optional[Dict[str, Any]]:
    for attempt in (1, 2):
        conn = None
        cur = None
        try:
            conn = get_conn()
            cur = conn.cursor()
            cur.execute(query, params)
            row = cur.fetchone()
            if not row:
                return None
            return _dict_from_cursor(cur, row)
        except Exception as e:
            if conn is not None and _is_retryable_db_error(e) and attempt == 1:
                _discard_conn(conn)
                conn = None
                continue
            raise
        finally:
            if cur is not None:
                try:
                    cur.close()
                except Exception:
                    pass
            if conn is not None:
                put_conn(conn)


def fetch_all(query: str, params: Tuple[Any, ...] = ()) -> List[Dict[str, Any]]:
    for attempt in (1, 2):
        conn = None
        cur = None
        try:
            conn = get_conn()
            cur = conn.cursor()
            cur.execute(query, params)
            rows = cur.fetchall() or []
            return [_dict_from_cursor(cur, r) for r in rows]
        except Exception as e:
            if conn is not None and _is_retryable_db_error(e) and attempt == 1:
                _discard_conn(conn)
                conn = None
                continue
            raise
        finally:
            if cur is not None:
                try:
                    cur.close()
                except Exception:
                    pass
            if conn is not None:
                put_conn(conn)


class _Tx:
    """The cursor handed out by transaction(): the same two verbs as the module."""

    def __init__(self, cur):
        self._cur = cur

    def execute(self, query: str, params: Tuple[Any, ...] = ()) -> int:
        """Run a statement; returns the number of rows it affected."""
        self._cur.execute(query, params)
        return self._cur.rowcount

    def fetch_one(self, query: str, params: Tuple[Any, ...] = ()) -> Optional[Dict[str, Any]]:
        self._cur.execute(query, params)
        row = self._cur.fetchone()
        return _dict_from_cursor(self._cur, row) if row else None


@contextmanager
def transaction():
    """
    Several statements, one commit. Everything inside the `with` happens or
    none of it does: an exception rolls the lot back and is re-raised.

        with transaction() as tx:
            tx.execute("UPDATE ...", (...))
            tx.execute("INSERT ...", (...))

    Unlike execute()/fetch_*, there is no retry on a dropped connection --
    replaying half a transaction is not safe, so the caller sees the error.
    """
    conn = get_conn()
    cur = None
    try:
        cur = conn.cursor()
        yield _Tx(cur)
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            # Cannot even roll back: the connection is broken, do not reuse it.
            _discard_conn(conn)
            conn = None
        raise
    finally:
        if cur is not None:
            try:
                cur.close()
            except Exception:
                pass
        if conn is not None:
            put_conn(conn)
