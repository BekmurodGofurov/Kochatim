# backend/middleware/require_api_key.py
from functools import wraps
from flask import g, request
from config import Config
from utils.errors import fail
from utils.security import safe_equal


def require_api_key(fn):
    """
    Bot-only route. The caller names whose data it touches (`u_id` in the
    request), so only the bot's service key is accepted -- never the web
    client key, which is public.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not Config.API_KEY:
            return fail("Server API_KEY is not configured", 500, code="SERVER_MISCONFIG")

        key = (request.headers.get("X-API-KEY") or "").strip()
        if not key or not safe_equal(key, Config.API_KEY):
            return fail("Unauthorized", 401, code="UNAUTHORIZED")
        g.client = "bot"
        return fn(*args, **kwargs)

    wrapper.auth_kind = "api_key"  # read by test_client_gate.py
    return wrapper
