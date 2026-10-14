from flask import g, request

from config import Config
from utils.errors import fail
from utils.security import safe_equal

OPEN_PATHS = frozenset({"/health"})

_IMAGE_ENDPOINT = "api.proxy_telegram_image"


def _matches(given: str, expected: str) -> bool:
    return bool(given) and bool(expected) and safe_equal(given, expected)


def enforce_client_key():
    """before_request hook. Returns a response to stop the request, else None."""
    g.client = None

    if request.method == "OPTIONS" or request.path in OPEN_PATHS:
        return None

    bot_key = (request.headers.get("X-API-KEY") or "").strip()
    if _matches(bot_key, Config.API_KEY):
        g.client = "bot"
        return None

    web_key = (request.headers.get("X-Client-Key") or "").strip()
    if not web_key and request.method == "GET" and request.endpoint == _IMAGE_ENDPOINT:
        web_key = (request.args.get("k") or "").strip()
    if _matches(web_key, Config.WEB_CLIENT_KEY):
        g.client = "web"
        return None

    return fail("Unauthorized", 401, code="UNAUTHORIZED")
