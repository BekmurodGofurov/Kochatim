# backend/auth/user_id_login.py
import threading
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
    try:
        # 1. Bazadan mavjud sessiyalarni olish
        rows = fetch_all(
            "SELECT token_hash FROM sessions WHERE u_id=%s ORDER BY created_at DESC",
            (u_id,),
        )
        
        # Sessiyalar sonini tekshirish va eskilarni o'chirish (yangi 1 ta qo'shilishi uchun joy ochamiz)
        if len(rows) >= _MAX_SESSIONS:
            keep = [r["token_hash"] for r in rows[:_MAX_SESSIONS - 1]]
            if keep:
                execute(
                    "DELETE FROM sessions WHERE u_id=%s AND token_hash <> ALL(%s)",
                    (u_id, keep),
                )
            else:
                execute("DELETE FROM sessions WHERE u_id=%s", (u_id,))

        # 2. Yangi sessiyani bazaga qo'shish (city boshlang'ich holatda bo'sh turadi)
        device_name = parse_device(user_agent)
        execute(
            "INSERT INTO sessions (token_hash, u_id, expires_at, device_name, ip_address, city) VALUES (%s, %s, %s, %s, %s, %s)",
            (token_hash, u_id, expires_at, device_name, ip, ""),
        )

        # 3. Shahar nomini aniqlash va sessiyani yangilash
        city = get_city(ip)
        if city:
            execute(
                "UPDATE sessions SET city=%s WHERE token_hash=%s",
                (city, token_hash),
            )
    except Exception as e:
        # Orqa fonda ishlaganligi sababli, xatoliklarni shu yerda ushlab qolish yaxshi amaliyotdir
        print(f"Background session insertion failed: {e}")


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
    
    # Sessiyani qo'shish va shaharni aniqlash kabi og'ir vazifalarni fonda ishga tushirish
    threading.Thread(
        target=_insert_session, 
        args=(token_hash, u_id, expires_at, ua, ip)
    ).start()

    # Foydalanuvchiga hech narsani kutmasdan darhol javob qaytarish
    return ok({"session_token": session_token, "u_id": u_id, "expires_in": Config.SESSION_TTL_SECONDS})
