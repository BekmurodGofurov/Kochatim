# backend/api/sessions.py
from flask import g, request
from api import api_bp
from middleware.require_session import require_session
from db import fetch_all, execute, fetch_one
from utils.errors import ok, fail
from utils.device import parse_device, get_city, get_client_ip


@api_bp.get("/sessions")
@require_session
def list_sessions():
    # Joriy session uchun device ma'lumotlari bo'sh bo'lsa — hozirgi so'rovdan to'ldiramiz
    cur = fetch_one(
        "SELECT device_name, ip_address FROM sessions WHERE token_hash = %s",
        (g.token_hash,),
    )
    if cur and not (cur.get("device_name") or "").strip():
        ua = request.headers.get("User-Agent", "")
        ip = get_client_ip(request)
        device_name = parse_device(ua)
        city = get_city(ip)
        execute(
            "UPDATE sessions SET device_name=%s, ip_address=%s, city=%s WHERE token_hash=%s",
            (device_name, ip, city, g.token_hash),
        )

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
