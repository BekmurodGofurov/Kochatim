# backend/middleware/require_api_key.py
from functools import wraps
from flask import request
from config import Config
from utils.errors import fail


def require_api_key(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not Config.API_KEY:
            return fail("Server API_KEY is not configured", 500, code="SERVER_MISCONFIG")

        key = (request.headers.get("X-API-KEY") or "").strip()
        if not key or key != Config.API_KEY:
            return fail("Unauthorized", 401, code="UNAUTHORIZED")
        return fn(*args, **kwargs)

    return wrapper