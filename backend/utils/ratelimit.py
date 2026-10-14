# backend/utils/ratelimit.py
"""
Fixed-window counters in Redis.

Two calls, deliberately separate, because the OTP check must count only
*failures* (a shared campus/office IP should not be locked out by people who
typed their code correctly):

    count(scope, ident, window)      -> how many so far this window
    record(scope, ident, window)     -> add one, return the new count

Both return None when Redis is unreachable. Whether that means "let it
through" or "refuse" is the caller's decision -- the login code refuses.
"""
import time

import utils.cache as _cache  # module attribute lookup: tests swap redis_client


def _key(scope: str, ident: str, window: int) -> str:
    return f"rl:{scope}:{ident}:{int(time.time()) // window}"


def retry_after(window: int) -> int:
    """Seconds until the current fixed window rolls over."""
    return window - (int(time.time()) % window)


def count(scope: str, ident: str, window: int):
    try:
        return int(_cache.redis_client.get(_key(scope, ident, window)) or 0)
    except Exception as e:
        print(f"Redis ratelimit GET error: {e}")
        return None


def record(scope: str, ident: str, window: int):
    key = _key(scope, ident, window)
    try:
        pipe = _cache.redis_client.pipeline()
        pipe.incr(key)
        pipe.expire(key, window)
        return int(pipe.execute()[0])
    except Exception as e:
        print(f"Redis ratelimit INCR error: {e}")
        return None
