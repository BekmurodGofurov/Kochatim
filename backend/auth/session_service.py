# backend/auth/session_service.py
"""
The one place a web session is created.

Both login paths (OTP and Telegram initData) end here, so the rules cannot
drift apart. Two things are decided by the server and never taken from the
caller: the IP address and the browser. `create_session` reads them from the
current Flask request itself and has no parameter to pass them in -- a body
field called `ip` or `device_name` has nowhere to go.
"""
from flask import request

from config import Config
from db import execute, fetch_all
from middleware.require_session import invalidate_session_cache
from utils.cache import invalidate_cache
from utils.device import client_fingerprint, get_city, get_client_ip, parse_device
from utils.device_proof import normalize_public_jwk
from utils.security import generate_token, sha256_hex
from utils.time import naive_utc, utc_in_seconds

MAX_SESSIONS = 3


class DeviceKeyError(ValueError):
    """The login request carried no usable device key."""


def parse_device_key(raw) -> str:
    """Validate the browser's public key; returns its canonical JSON."""
    try:
        return normalize_public_jwk(raw)
    except (ValueError, TypeError) as e:
        raise DeviceKeyError(str(e))


def create_session(u_id: int, device_key: str) -> str:
    """
    Insert a session bound to `device_key` (from parse_device_key) and return
    the raw token. Only the SHA-256 of the token is stored.
    """
    token = generate_token(32)
    token_hash = sha256_hex(token)
    expires_at = naive_utc(utc_in_seconds(Config.SESSION_TTL_SECONDS))

    user_agent = request.headers.get("User-Agent", "")
    ip = get_client_ip(request)

    execute(
        """
        INSERT INTO sessions
            (token_hash, u_id, expires_at, device_name, ip_address, city, device_key, ua_fp)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            token_hash, u_id, expires_at,
            parse_device(user_agent), ip, get_city(ip),
            device_key, client_fingerprint(user_agent),
        ),
    )

    # Keep only the newest MAX_SESSIONS and make sure the dropped ones stop
    # working immediately rather than when their cache entry expires.
    rows = fetch_all(
        "SELECT token_hash FROM sessions WHERE u_id=%s ORDER BY created_at DESC, session_id DESC",
        (u_id,),
    )
    if len(rows) > MAX_SESSIONS:
        keep = [r["token_hash"] for r in rows[:MAX_SESSIONS]]
        execute(
            "DELETE FROM sessions WHERE u_id=%s AND token_hash <> ALL(%s)",
            (u_id, keep),
        )
        for r in rows[MAX_SESSIONS:]:
            invalidate_session_cache(r["token_hash"])

    invalidate_cache(f"sessions_{u_id}")
    invalidate_cache(f"settings_{u_id}")
    return token
