# backend/middleware/require_session.py
from functools import wraps
from flask import request, g
from utils.errors import fail
from utils.security import sha256_hex
from db import fetch_one


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

        sess = fetch_one(
            """
            SELECT u_id
            FROM sessions
            WHERE token_hash=%s
              AND (expires_at IS NULL OR expires_at > NOW())
            """,
            (token_hash,),
        )
        if not sess:
            return fail("Unauthorized", 401, code="UNAUTHORIZED")

        g.u_id = int(sess["u_id"])
        return fn(*args, **kwargs)

    return wrapper