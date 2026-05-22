# backend/auth/telegram_webapp.py
from flask import request
from auth import auth_bp
from config import Config
from db import execute, fetch_one, fetch_all
from utils.errors import ok, fail
from utils.security import telegram_webapp_verify, parse_telegram_user, generate_token, sha256_hex
from utils.time import utc_in_seconds, naive_utc
from utils.device import parse_device, get_city, get_client_ip

_MAX_SESSIONS = 3


def _insert_session(token_hash, u_id, expires_at, user_agent="", ip=""):
    device_name = parse_device(user_agent)
    city = get_city(ip)
    execute(
        "INSERT INTO sessions (token_hash, u_id, expires_at, device_name, ip_address, city) VALUES (%s, %s, %s, %s, %s, %s)",
        (token_hash, u_id, expires_at, device_name, ip, city),
    )
    rows = fetch_all(
        "SELECT token_hash FROM sessions WHERE u_id=%s ORDER BY created_at DESC",
        (u_id,),
    )
    if len(rows) > _MAX_SESSIONS:
        keep = [r["token_hash"] for r in rows[:_MAX_SESSIONS]]
        execute(
            "DELETE FROM sessions WHERE u_id=%s AND token_hash <> ALL(%s)",
            (u_id, keep),
        )


@auth_bp.post("/telegram-webapp")
def telegram_webapp_login():
    """
    Mini App yuboradi:
    body: { initData: "..." }
    return: { session_token, u_id, is_registered }
    """
    data = request.get_json(silent=True) or {}
    init_data = data.get("initData") or ""
    
    try:
        parsed = telegram_webapp_verify(init_data, Config.BOT_TOKEN)
        uinfo = parse_telegram_user(parsed)
    except Exception as e:
        return fail("Invalid initData", 401, code="INVALID_INITDATA", extra=str(e))

    u_id = uinfo["u_id"]
    u_name = uinfo["u_name"] or None
    u_username = uinfo["u_username"] or None

    # UPSERT user (phone/age bu yo'lda kelmaydi odatda)
    execute("""
    INSERT INTO users (u_id, u_name, u_username)
    VALUES (%s, %s, %s)
    ON CONFLICT (u_id) DO UPDATE SET
        u_name = COALESCE(EXCLUDED.u_name, users.u_name),
        u_username = COALESCE(EXCLUDED.u_username, users.u_username)
    """, (u_id, u_name, u_username))

    token = generate_token(32)
    token_hash = sha256_hex(token)
    expires_at = naive_utc(utc_in_seconds(Config.SESSION_TTL_SECONDS))

    ua = request.headers.get("User-Agent", "")
    ip = get_client_ip(request)
    _insert_session(token_hash, u_id, expires_at, ua, ip)

    # Foydalanuvchi ma'lumotlarini tekshirish
    user = fetch_one("SELECT u_phone FROM users WHERE u_id=%s", (u_id,))

    return ok({
        "session_token": token, 
        "u_id": u_id,
        "is_registered": bool(user and user.get("u_phone"))
    })