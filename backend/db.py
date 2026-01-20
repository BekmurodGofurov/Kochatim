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