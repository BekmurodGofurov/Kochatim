from flask import g, request

from api import api_bp
from db import execute, fetch_all, fetch_one
from middleware.require_api_key import require_api_key
from middleware.require_session import require_session
from utils.errors import ok, fail
from utils.security import generate_invite_token
from utils.time import utc_in_seconds, naive_utc
from config import Config

INVITE_TTL_SECONDS = 7 * 24 * 3600  # 7 kun


def _partner_exists(u_id: int, p_id: int) -> bool:
    row = fetch_one("SELECT 1 FROM partners WHERE u_id=%s AND p_id=%s", (u_id, p_id))
    return bool(row)


@api_bp.get("/partners")
@require_session
def list_partners_me():
    u_id = int(g.u_id)
    rows = fetch_all(
        """
        SELECT u.u_id, u.u_name, u.u_phone, u.u_username, u.u_age, u.u_photo, p.created_at
        FROM partners p
        JOIN users u ON u.u_id = p.p_id
        WHERE p.u_id=%s
        ORDER BY p.created_at DESC
        """,
        (u_id,),
    )
    return ok(rows)


@api_bp.post("/partners/remove")
@require_session
def remove_partner_me():
    u_id = int(g.u_id)
    data = request.get_json(silent=True) or {}
    p_id = data.get("p_id")
    try:
        p_id = int(p_id)
    except Exception:
        return fail("p_id(int) required", 400)

    execute("DELETE FROM partners WHERE (u_id=%s AND p_id=%s) OR (u_id=%s AND p_id=%s)", (u_id, p_id, p_id, u_id))
    return ok({"removed": True, "p_id": p_id})


@api_bp.get("/partners/invite-token")
@require_session
def get_partner_invite_token():
    u_id = int(g.u_id)

    token = generate_invite_token()
    expires_at = naive_utc(utc_in_seconds(INVITE_TTL_SECONDS))

    execute(
        "INSERT INTO partner_invites (token, inviter_u_id, expires_at) VALUES (%s, %s, %s)",
        (token, u_id, expires_at),
    )

    return ok({"token": token, "bot_username": Config.TG_BOT_USERNAME})


@api_bp.post("/partners/accept")
@require_api_key
def accept_partner_invite():
    """Bot chaqiradi (X-API-KEY). body: { token, u_id }"""
    data = request.get_json(silent=True) or {}
    token = (data.get("token") or "").strip()
    invitee_u_id = data.get("u_id")
    try:
        invitee_u_id = int(invitee_u_id)
    except Exception:
        return fail("u_id(int) required", 400)

    if not token:
        return fail("token required", 400)

    invite = fetch_one(
        "SELECT inviter_u_id, expires_at, used_at FROM partner_invites WHERE token=%s",
        (token,),
    )
    if not invite:
        return fail("Invalid invite token", 400, code="INVALID_TOKEN")

    from utils.time import utcnow
    now = naive_utc(utcnow())
    if invite["used_at"] is not None:
        return fail("Invite already used", 400, code="INVITE_USED")
    if invite["expires_at"] <= now:
        return fail("Invite expired", 400, code="INVITE_EXPIRED")

    inviter_u_id = int(invite["inviter_u_id"])

    if inviter_u_id == invitee_u_id:
        return fail("Cannot partner with yourself", 400, code="SELF")

    inviter = fetch_one("SELECT u_id FROM users WHERE u_id=%s", (inviter_u_id,))
    invitee = fetch_one("SELECT u_id FROM users WHERE u_id=%s", (invitee_u_id,))
    if not inviter or not invitee:
        return fail("User not found", 404, code="NOT_FOUND")

    execute("UPDATE partner_invites SET used_at=%s WHERE token=%s", (now, token))

    if not _partner_exists(inviter_u_id, invitee_u_id):
        execute("INSERT INTO partners (u_id, p_id) VALUES (%s, %s) ON CONFLICT DO NOTHING", (inviter_u_id, invitee_u_id))
    if not _partner_exists(invitee_u_id, inviter_u_id):
        execute("INSERT INTO partners (u_id, p_id) VALUES (%s, %s) ON CONFLICT DO NOTHING", (invitee_u_id, inviter_u_id))

    return ok({"accepted": True, "inviter_u_id": inviter_u_id, "invitee_u_id": invitee_u_id})


@api_bp.post("/partners/decline")
@require_api_key
def decline_partner_invite():
    """Bot chaqiradi (X-API-KEY). body: { token, u_id }"""
    data = request.get_json(silent=True) or {}
    token = (data.get("token") or "").strip()
    invitee_u_id = data.get("u_id")
    try:
        invitee_u_id = int(invitee_u_id)
    except Exception:
        return fail("u_id(int) required", 400)

    if not token:
        return fail("token required", 400)

    invite = fetch_one(
        "SELECT inviter_u_id, expires_at, used_at FROM partner_invites WHERE token=%s",
        (token,),
    )
    if not invite:
        return fail("Invalid invite token", 400, code="INVALID_TOKEN")

    inviter_u_id = int(invite["inviter_u_id"])
    return ok({"declined": True, "inviter_u_id": inviter_u_id, "invitee_u_id": invitee_u_id})
