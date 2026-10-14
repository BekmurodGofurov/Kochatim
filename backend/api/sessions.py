# backend/api/sessions.py
from flask import g
from api import api_bp
from middleware.require_session import require_session, invalidate_session_cache, revoke_session
from db import fetch_all, execute, fetch_one
from utils.errors import ok, fail
from utils.cache import get_cache, set_cache, invalidate_cache

_SESSIONS_TTL = 120  # 2 daqiqa


def _sessions_key(u_id: int) -> str:
    return f"sessions_{u_id}"


def session_rows(u_id: int) -> list:
    """
    The user's live sessions, newest first. Safe to cache per user: it holds
    no per-viewer state. `token_hash` stays in so the caller can mark which
    row is theirs -- present_sessions() strips it before anything is sent.
    """
    rows = fetch_all(
        """
        SELECT session_id, device_name, city, ip_address, created_at, token_hash
        FROM sessions
        WHERE u_id = %s
          AND (expires_at IS NULL OR expires_at > (NOW() AT TIME ZONE 'utc'))
        ORDER BY created_at DESC
        """,
        (u_id,),
    )
    return [
        {
            "session_id": r["session_id"],
            "device_name": r["device_name"] or "",
            "city": r["city"] or "",
            "ip_address": r["ip_address"] or "",
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            "token_hash": r["token_hash"],
        }
        for r in rows
    ]


def present_sessions(rows: list, current_hash) -> list:
    """Add is_current for *this* request's session and drop the token hash."""
    return [
        {**{k: v for k, v in r.items() if k != "token_hash"},
         "is_current": r["token_hash"] == current_hash}
        for r in rows
    ]


@api_bp.get("/sessions")
@require_session
def list_sessions():
    u_id = int(g.u_id)

    key = _sessions_key(u_id)
    rows = get_cache(key)
    if rows is None:
        rows = session_rows(u_id)
        set_cache(key, rows, ttl=_SESSIONS_TTL)
    return ok(present_sessions(rows, g.token_hash))


@api_bp.delete("/sessions/<int:session_id>")
@require_session
def delete_session(session_id):
    u_id = int(g.u_id)
    row = fetch_one(
        "SELECT session_id, token_hash FROM sessions WHERE session_id = %s AND u_id = %s",
        (session_id, u_id),
    )
    if not row:
        return fail("Session topilmadi", 404)

    execute(
        "DELETE FROM sessions WHERE session_id = %s AND u_id = %s",
        (session_id, u_id),
    )

    # O'chirilgan sessiyaning token keshini ham tozalaymiz
    if row.get("token_hash"):
        invalidate_session_cache(row["token_hash"])
    invalidate_cache(_sessions_key(u_id))
    invalidate_cache(f"settings_{u_id}")

    return ok({"deleted": True})



@api_bp.post("/logout")
@require_session
def logout():
    """End the current session on the server, not just in the browser."""
    revoke_session(g.token_hash, int(g.u_id))
    return ok({"logged_out": True})
