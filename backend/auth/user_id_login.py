# backend/auth/user_id_login.py
from flask import request
from auth import auth_bp
from utils.errors import ok, fail
from utils.security import random_token, sha256_hex
from utils.time import utcnow_plus_seconds
from config import Config
from db import execute, fetch_one, fetch_all


@auth_bp.post("/user-id-login")
def user_id_login():
    data = request.get_json(silent=True) or {}

    # user id faqat raqam
    try:
        u_id = int(data.get("u_id"))
    except Exception:
        return fail("u_id(int) required", 400)

    # user borligini tekshiramiz
    user = fetch_one("SELECT u_id FROM users WHERE u_id=%s", (u_id,))
    if not user:
        # hozircha shunaqa: botga /start qilish kerak
        return fail("User not found. Please open Telegram bot and run /start", 404, code="USER_NOT_FOUND")

    # token yaratish
    session_token = random_token(32)          # clientga qaytadi (64 hex)
    token_hash = sha256_hex(session_token)    # DBga yoziladi

    expires_at = utcnow_plus_seconds(Config.SESSION_TTL_SECONDS)

    # yangi sessiyani yozamiz
    execute(
        """
        INSERT INTO sessions (token_hash, u_id, expires_at)
        VALUES (%s, %s, %s)
        """,
        (token_hash, u_id, expires_at),
    )

    # ✅ faqat oxirgi 5 ta session qolsin (qolgani o'chsin)
    # created_at eng yangisi tepada.
    rows = fetch_all(
        """
        SELECT token_hash
        FROM sessions
        WHERE u_id=%s
        ORDER BY created_at DESC
        """,
        (u_id,),
    )

    if rows and len(rows) > 5:
        keep_hashes = [r["token_hash"] for r in rows[:5]]
        # keep ro'yxatidan tashqaridagilarni o'chiramiz
        execute(
            """
            DELETE FROM sessions
            WHERE u_id=%s
              AND token_hash <> ALL(%s)
            """,
            (u_id, keep_hashes),
        )

    return ok({"session_token": session_token, "u_id": u_id, "expires_in": Config.SESSION_TTL_SECONDS})