from typing import Optional
from psycopg2.pool import ThreadedConnectionPool

from config import Config

_pool: Optional[ThreadedConnectionPool] = None


def init_pool():
    global _pool
    if _pool is not None:
        return

    _pool = ThreadedConnectionPool(
        minconn=Config.DB_POOL_MIN,
        maxconn=Config.DB_POOL_MAX,
        dsn=Config.DATABASE_URL,
    )


def get_pool() -> ThreadedConnectionPool:
    global _pool
    if _pool is None:
        init_pool()
    assert _pool is not None
    return _pool


def get_conn():
    """
    Pooldan bitta connection beradi.
    """
    pool = get_pool()
    return pool.getconn()


def put_conn(conn, close: bool = False):
    """
    Connectionni poolga qaytaradi.
    close=True bo'lsa pool uni yopib tashlaydi (discard).
    """
    pool = get_pool()
    # psycopg2 ThreadedConnectionPool putconn(close=True) ni qo'llab-quvvatlaydi
    pool.putconn(conn, close=close)