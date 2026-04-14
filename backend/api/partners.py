from flask import g, request

from api import api_bp
from db import execute, fetch_all, fetch_one
from middleware.require_api_key import require_api_key
from middleware.require_session import require_session
from utils.errors import ok, fail
from utils.invite_tokens import make_partner_invite_token, parse_partner_invite_token
from config import Config


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
    if not u_id:
        return fail("Unauthorized", 401, code="UNAUTHORIZED")

    token = make_partner_invite_token(u_id)
    return ok({"token": token, "bot_username": Config.TG_BOT_USERNAME})


@api_bp.post("/partners/accept")
@require_api_key
def accept_partner_invite():
    """
    Called by Telegram bot (X-API-KEY) after user confirms.
    body: { token: "...", u_id: inviteeTelegramId }
    """
    data = request.get_json(silent=True) or {}
    token = (data.get("token") or "").strip()
    invitee_u_id = data.get("u_id")
    try:
        invitee_u_id = int(invitee_u_id)
    except Exception:
        return fail("u_id(int) required", 400)

    payload, err = parse_partner_invite_token(token)
    if err:
        return fail("Invalid token", 400, code=err)

    inviter_u_id = int(payload["inviter"])
    if inviter_u_id == invitee_u_id:
        return fail("Cannot partner with yourself", 400, code="SELF")

    # Ensure both users exist
    inviter = fetch_one("SELECT u_id FROM users WHERE u_id=%s", (inviter_u_id,))
    invitee = fetch_one("SELECT u_id FROM users WHERE u_id=%s", (invitee_u_id,))
    if not inviter or not invitee:
        return fail("User not found", 404, code="NOT_FOUND")

    # Insert symmetric relation (idempotent)
    if not _partner_exists(inviter_u_id, invitee_u_id):
        execute("INSERT INTO partners (u_id, p_id) VALUES (%s, %s) ON CONFLICT DO NOTHING", (inviter_u_id, invitee_u_id))
    if not _partner_exists(invitee_u_id, inviter_u_id):
        execute("INSERT INTO partners (u_id, p_id) VALUES (%s, %s) ON CONFLICT DO NOTHING", (invitee_u_id, inviter_u_id))

    return ok({"accepted": True, "inviter_u_id": inviter_u_id, "invitee_u_id": invitee_u_id})


@api_bp.post("/partners/decline")
@require_api_key
def decline_partner_invite():
    """
    Called by Telegram bot.
    body: { token: "...", u_id: inviteeTelegramId }
    """
    data = request.get_json(silent=True) or {}
    token = (data.get("token") or "").strip()
    invitee_u_id = data.get("u_id")
    try:
        invitee_u_id = int(invitee_u_id)
    except Exception:
        return fail("u_id(int) required", 400)

    payload, err = parse_partner_invite_token(token)
    if err:
        return fail("Invalid token", 400, code=err)

    inviter_u_id = int(payload["inviter"])
    return ok({"declined": True, "inviter_u_id": inviter_u_id, "invitee_u_id": invitee_u_id})

