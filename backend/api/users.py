from flask import request, g
from api import api_bp
from middleware.require_api_key import require_api_key
from middleware.require_session import require_session
from utils.errors import ok, fail
from utils.cache import get_cache, set_cache
from utils.security import generate_invite_token
from utils.time import utc_in_seconds, naive_utc, utcnow
from utils.device import parse_device, get_city, get_client_ip
from db import execute, fetch_one, fetch_all
from config import Config

@api_bp.get("/me")
@require_session
def get_me():
    u_id = int(g.u_id)

    row = fetch_one(
        """
        SELECT u_id, u_name, u_phone, u_username, u_age, added_at, updated_at
        FROM users
        WHERE u_id=%s
        """,
        (u_id,),
    )
    if not row:
        return fail("User not found", 404, code="NOT_FOUND")

    return ok(row)

@api_bp.post("/users/ensure")
@require_api_key
def ensure_user():
    data = request.get_json(silent=True) or {}
    u_id = data.get("u_id")
    if not isinstance(u_id, int):
        return fail("u_id(int) required", 400)

    u_name = (data.get("u_name") or "").strip() or None
    u_phone = (data.get("u_phone") or "").strip() or None
    u_username = (data.get("u_username") or "").strip() or None
    u_photo = (data.get("u_photo") or "").strip() or None

    u_age = data.get("u_age")
    if u_age is not None:
        try:
            u_age = int(u_age)
        except Exception:
            u_age = None

    execute(
        """
        INSERT INTO users (u_id, u_name, u_phone, u_username, u_age, u_photo)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (u_id) DO UPDATE SET
            u_name = COALESCE(EXCLUDED.u_name, users.u_name),
            u_phone = COALESCE(EXCLUDED.u_phone, users.u_phone),
            u_username = COALESCE(EXCLUDED.u_username, users.u_username),
            u_age = COALESCE(EXCLUDED.u_age, users.u_age),
            u_photo = COALESCE(EXCLUDED.u_photo, users.u_photo)
        """,
        (u_id, u_name, u_phone, u_username, u_age, u_photo),
    )

    row = fetch_one(
        "SELECT u_id, u_name, u_phone, u_username, u_age, added_at, updated_at FROM users WHERE u_id=%s",
        (u_id,),
    )
    return ok(row)


@api_bp.get("/users/<int:u_id>")
@require_api_key
def get_user(u_id: int):
    row = fetch_one(
        "SELECT u_id, u_name, u_phone, u_username, u_age, added_at, updated_at FROM users WHERE u_id=%s",
        (u_id,),
    )
    if not row:
        return fail("User not found", 404, code="NOT_FOUND")
    return ok(row)


@api_bp.get("/me/settings")
@require_session
def settings_me():
    """
    Settings sahifasi uchun barcha ma'lumotlar bitta so'rovda:
    partners + sessions + invite_token
    """
    u_id = int(g.u_id)
    key = f"settings_{u_id}"

    cached = get_cache(key)
    if cached is not None:
        return ok(cached)

    # 1. Hamkorlar
    partners = fetch_all(
        """
        SELECT u.u_id, u.u_name, u.u_phone, u.u_username, u.u_age, u.u_photo, p.created_at
        FROM partners p
        JOIN users u ON u.u_id = p.p_id
        WHERE p.u_id = %s
        ORDER BY p.created_at DESC
        """,
        (u_id,),
    )

    # 2. Sessiyalar (device nomini bir marta to'ldirish)
    cur = fetch_one(
        "SELECT device_name FROM sessions WHERE token_hash = %s",
        (g.token_hash,),
    )
    if cur and not (cur.get("device_name") or "").strip():
        ua = request.headers.get("User-Agent", "")
        ip = get_client_ip(request)
        execute(
            "UPDATE sessions SET device_name=%s, ip_address=%s, city=%s WHERE token_hash=%s",
            (parse_device(ua), ip, get_city(ip), g.token_hash),
        )

    session_rows = fetch_all(
        """
        SELECT session_id, device_name, city, ip_address, created_at, token_hash
        FROM sessions
        WHERE u_id = %s
          AND (expires_at IS NULL OR expires_at > (NOW() AT TIME ZONE 'utc'))
        ORDER BY created_at DESC
        """,
        (u_id,),
    )
    current_hash = getattr(g, "token_hash", None)
    sessions = [
        {
            "session_id":  r["session_id"],
            "device_name": r["device_name"] or "",
            "city":        r["city"] or "",
            "ip_address":  r["ip_address"] or "",
            "created_at":  r["created_at"].isoformat() if r["created_at"] else None,
            "is_current":  r["token_hash"] == current_hash,
        }
        for r in session_rows
    ]

    # 3. Invite token — mavjudini ishlatamiz, yangi yaratamasmiz
    now = naive_utc(utcnow())
    existing = fetch_one(
        """
        SELECT token FROM partner_invites
        WHERE inviter_u_id = %s AND used_at IS NULL AND expires_at > %s
        ORDER BY expires_at DESC LIMIT 1
        """,
        (u_id, now),
    )
    if existing:
        invite_token = existing["token"]
    else:
        invite_token = generate_invite_token()
        expires_at = naive_utc(utc_in_seconds(7 * 24 * 3600))
        execute(
            "INSERT INTO partner_invites (token, inviter_u_id, expires_at) VALUES (%s, %s, %s)",
            (invite_token, u_id, expires_at),
        )

    data = {
        "partners":     partners,
        "sessions":     sessions,
        "invite_token": invite_token,
        "bot_username": Config.TG_BOT_USERNAME,
    }
    set_cache(key, data, ttl=120)  # 2 daqiqa (sessions o'zgaruvchan)
    return ok(data)


@api_bp.get("/gardeners")
def search_gardeners():
    """
    Public: search of gardeners (bog'bonlar).
    query params:
      - q: by u_id exact or u_name/u_username partial
      - limit: default 12 (max 50)
    """
    q = (request.args.get("q") or "").strip()
    limit = request.args.get("limit", type=int) or 12
    limit = max(1, min(limit, 50))

    params = []
    where = ["u_phone IS NOT NULL"]

    # If numeric -> match u_id first
    if q:
        try:
            u_id = int(q)
            where.append("u_id=%s")
            params.append(u_id)
        except Exception:
            where.append("(u_name ILIKE %s OR u_username ILIKE %s)")
            like = f"%{q}%"
            params.extend([like, like])

    rows = fetch_all(
        f"""
        SELECT u_id, u_name, u_username, u_phone, u_photo, added_at
        FROM users
        WHERE {' AND '.join(where)}
        ORDER BY added_at DESC
        LIMIT %s
        """,
        tuple(params + [limit]),
    )
    return ok(rows)
