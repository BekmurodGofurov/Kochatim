# backend/api/sessions.py
from flask import g
from api import api_bp
from middleware.require_session import require_session
from db import fetch_all, execute, fetch_one
from utils.errors import ok, fail


@api_bp.get("/sessions")
@require_session
def list_sessions():
    rows = fetch_all(
        """
        SELECT session_id, device_name, city, ip_address, created_at, token_hash
        FROM sessions
        WHERE u_id = %s
          AND (expires_at IS NULL OR expires_at > (NOW() AT TIME ZONE 'utc'))
        ORDER BY created_at DESC
        """,
        (g.u_id,),
    )
    current_hash = getattr(g, "token_hash", None)
    result = []
    for r in rows:
        result.append({
            "session_id": r["session_id"],
            "device_name": r["device_name"] or "",
            "city": r["city"] or "",
            "ip_address": r["ip_address"] or "",
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            "is_current": r["token_hash"] == current_hash,
        })
    return ok(result)


@api_bp.delete("/sessions/<int:session_id>")
@require_session
def delete_session(session_id):
    row = fetch_one(
        "SELECT session_id FROM sessions WHERE session_id = %s AND u_id = %s",
        (session_id, g.u_id),
    )
    if not row:
        return fail("Session topilmadi", 404)
    execute(
        "DELETE FROM sessions WHERE session_id = %s AND u_id = %s",
        (session_id, g.u_id),
    )
    return ok({"deleted": True})
