# backend/middleware/require_session.py
"""
Web-client authentication.

A session is not just a bearer token. It is a token *and* the device key the
browser registered at login (utils/device_proof.py): every request must also
carry a fresh signature made with that key. A token copied out of
localStorage into another browser therefore fails here -- it has nothing to
sign with.

Checks, in order, all of which must pass:
  1. the request came through the gate as the web client
  2. a Bearer token that maps to a live session with a device key
  3. a valid, fresh, single-use X-Session-Proof for this exact request
  4. the browser/OS family is the one the session was created from

The reason for a rejection is logged, never returned: every failure is the
same bare 401.
"""
from functools import wraps
from flask import current_app, g, request
from config import Config
from utils.errors import fail
from utils.security import sha256_hex
from utils.cache import get_cache, set_cache, invalidate_cache, claim_once
from utils.device import client_fingerprint
from utils.device_proof import ProofError, verify_proof
from db import fetch_one, execute

_SESSION_CACHE_TTL = 120  # 2 daqiqa


def _session_key(token_hash: str) -> str:
    return f"session_{token_hash}"


def invalidate_session_cache(token_hash: str):
    invalidate_cache(_session_key(token_hash))


def revoke_session(token_hash: str, u_id: int):
    """Delete one session and every cache entry that could still vouch for it."""
    execute("DELETE FROM sessions WHERE token_hash=%s", (token_hash,))
    invalidate_session_cache(token_hash)
    invalidate_cache(f"sessions_{u_id}")
    invalidate_cache(f"settings_{u_id}")


def _reject(reason: str):
    current_app.logger.warning("session rejected: %s (%s %s)", reason, request.method, request.path)
    return None


def _request_target() -> str:
    """
    The request target exactly as the browser sent -- and signed -- it.

    gunicorn hands over the raw request line as RAW_URI, which keeps
    percent-encoding intact (nginx forwards it untouched when proxy_pass has
    no URI part). Flask's request.path is already decoded, so it is only the
    fallback for servers that do not provide RAW_URI.
    """
    raw = request.environ.get("RAW_URI")
    if raw and raw.startswith("/"):
        return raw
    qs = request.query_string.decode("utf-8", errors="replace")
    return f"{request.path}?{qs}" if qs else request.path


def _load_session(token_hash: str):
    cached = get_cache(_session_key(token_hash))
    # Entries written before device binding were a bare u_id: treat as a miss.
    if isinstance(cached, dict) and cached.get("device_key"):
        return cached

    row = fetch_one(
        """
        SELECT u_id, device_key, ua_fp
        FROM sessions
        WHERE token_hash=%s
          AND (expires_at IS NULL OR expires_at > (NOW() AT TIME ZONE 'utc'))
        """,
        (token_hash,),
    )
    # A session with no device key predates binding and is never honoured.
    if not row or not row.get("device_key"):
        return None
    sess = {
        "u_id": int(row["u_id"]),
        "device_key": row["device_key"],
        "ua_fp": row.get("ua_fp") or "",
    }
    set_cache(_session_key(token_hash), sess, ttl=_SESSION_CACHE_TTL)
    return sess


def _authenticate():
    """Return (u_id, token_hash) for a fully proven request, else None."""
    if getattr(g, "client", None) != "web":
        return _reject("not the web client")

    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None  # nothing presented; not worth a log line
    token = auth.split(" ", 1)[1].strip()
    if not token:
        return None

    token_hash = sha256_hex(token)
    sess = _load_session(token_hash)
    if sess is None:
        return _reject("unknown or expired session")

    try:
        nonce = verify_proof(
            request.headers.get("X-Session-Proof"),
            method=request.method,
            target=_request_target(),
            token=token,
            public_jwk=sess["device_key"],
            max_skew_seconds=Config.PROOF_MAX_SKEW_SECONDS,
        )
    except ProofError as e:
        return _reject(f"proof {e}")

    claimed = claim_once(
        f"proof:{token_hash[:16]}:{nonce}", ttl=Config.PROOF_MAX_SKEW_SECONDS * 2
    )
    if claimed is False:
        return _reject("proof replayed")
    if claimed is None:
        # Redis is down. The signature and the timestamp window still hold,
        # so a captured proof is only reusable for PROOF_MAX_SKEW_SECONDS.
        current_app.logger.error("proof nonce check skipped: Redis unavailable")

    # Last, and only after the signature proved this really is the key
    # holder: a different browser/OS family than at login ends the session.
    # (Doing it before the proof would let anyone holding a stolen token log
    # the victim out just by sending an odd User-Agent.)
    stored_fp = sess.get("ua_fp") or ""
    if stored_fp and stored_fp != client_fingerprint(request.headers.get("User-Agent", "")):
        revoke_session(token_hash, int(sess["u_id"]))
        return _reject("browser changed")

    return int(sess["u_id"]), token_hash


def require_session(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        result = _authenticate()
        if result is None:
            return fail("Unauthorized", 401, code="UNAUTHORIZED")
        g.u_id, g.token_hash = result
        return fn(*args, **kwargs)

    wrapper.auth_kind = "session"  # read by test_client_gate.py
    return wrapper


def get_viewer():
    """
    The logged-in user's u_id, or None for an anonymous / unproven caller.

    For public routes that show more to a signed-in viewer. Unlike
    require_session it never rejects: a bad or missing credential just means
    "anonymous", and the route falls back to its public answer.
    """
    result = _authenticate()
    if result is None:
        return None
    g.u_id, g.token_hash = result
    return result[0]
