# backend/auth/user_id_login.py
from flask import request
from auth import auth_bp
from utils.errors import ok, fail
from utils.security import random_token, sha256_hex
from utils.time import utcnow_plus_seconds
from utils.device import parse_device, get_city, get_client_ip
from config import Config
from db import execute, fetch_one, fetch_all

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


@auth_bp.post("/user-id-login")
def user_id_login():
    data = request.get_json(silent=True) or {}

    try:
        u_id = int(data.get("u_id"))
    except Exception:
        return fail("u_id(int) required", 400)

    user = fetch_one("SELECT u_id FROM users WHERE u_id=%s", (u_id,))
    if not user:
        return fail("User not found. Please open Telegram bot and run /start", 404, code="USER_NOT_FOUND")

    session_token = random_token(32)
    token_hash = sha256_hex(session_token)
    expires_at = utcnow_plus_seconds(Config.SESSION_TTL_SECONDS)

    ua = request.headers.get("User-Agent", "")
    ip = get_client_ip(request)
    _insert_session(token_hash, u_id, expires_at, ua, ip)

    return ok({"session_token": session_token, "u_id": u_id, "expires_in": Config.SESSION_TTL_SECONDS})
