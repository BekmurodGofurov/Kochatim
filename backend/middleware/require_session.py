# backend/middleware/require_session.py
from functools import wraps
from flask import request, g
from utils.errors import fail
from utils.security import sha256_hex
from utils.cache import get_cache, set_cache, invalidate_cache
from db import fetch_one

_SESSION_CACHE_TTL = 120  # 2 daqiqa


def _session_key(token_hash: str) -> str:
    return f"session_{token_hash}"


def invalidate_session_cache(token_hash: str):
    invalidate_cache(_session_key(token_hash))


def require_session(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return fail("Unauthorized", 401, code="UNAUTHORIZED")

        token = auth.split(" ", 1)[1].strip()
        if not token:
            return fail("Unauthorized", 401, code="UNAUTHORIZED")

        token_hash = sha256_hex(token)
        cache_key = _session_key(token_hash)

        u_id = get_cache(cache_key)
        if u_id is None:
            sess = fetch_one(
                """
                SELECT u_id
                FROM sessions
                WHERE token_hash=%s
                  AND (expires_at IS NULL OR expires_at > (NOW() AT TIME ZONE 'utc'))
                """,
                (token_hash,),
            )
            if not sess:
                return fail("Unauthorized", 401, code="UNAUTHORIZED")
            u_id = int(sess["u_id"])
            set_cache(cache_key, u_id, ttl=_SESSION_CACHE_TTL)

        g.u_id = u_id
        g.token_hash = token_hash
        return fn(*args, **kwargs)

    return wrapper
