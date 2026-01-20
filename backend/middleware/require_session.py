# backend/middleware/require_session.py
from functools import wraps
from flask import request, g
from db import fetch_one
from utils.errors import fail
from utils.security import sha256_hex
from utils.time import utcnow, naive_utc


def require_session(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth = (request.headers.get("Authorization") or "").strip()
        if not auth.startswith("Bearer "):
            return fail("Unauthorized", 401, code="UNAUTHORIZED")

        token = auth.replace("Bearer ", "", 1).strip()
        if not token:
            return fail("Unauthorized", 401, code="UNAUTHORIZED")

        token_hash = sha256_hex(token)
        row = fetch_one("SELECT u_id, expires_at FROM sessions WHERE token_hash=%s", (token_hash,))
        if not row:
            return fail("Unauthorized", 401, code="UNAUTHORIZED")

        now = naive_utc(utcnow())
        if row["expires_at"] <= now:
            return fail("Session expired", 401, code="SESSION_EXPIRED")

        g.u_id = int(row["u_id"])
        return fn(*args, **kwargs)

    return wrapper