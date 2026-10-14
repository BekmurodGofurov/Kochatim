# backend/auth/telegram_webapp.py
from flask import current_app, request
from auth import auth_bp
from auth.session_service import DeviceKeyError, create_session, parse_device_key
from config import Config
from db import execute, fetch_one
from utils.errors import ok, fail
from utils.security import telegram_webapp_verify, parse_telegram_user


@auth_bp.post("/telegram-webapp")
def telegram_webapp_login():
    """
    Mini App yuboradi:
    body: { initData: "...", device_key: {public JWK} }
    return: { session_token, u_id, is_registered }
    """
    data = request.get_json(silent=True) or {}
    init_data = data.get("initData")
    init_data = init_data if isinstance(init_data, str) else ""

    try:
        device_key = parse_device_key(data.get("device_key"))
    except DeviceKeyError:
        return fail("device_key required", 400, code="DEVICE_KEY_REQUIRED")

    try:
        parsed = telegram_webapp_verify(
            init_data, Config.BOT_TOKEN, max_age_seconds=Config.INITDATA_MAX_AGE_SECONDS
        )
        uinfo = parse_telegram_user(parsed)
    except Exception as e:
        # The reason (bad hash, stale auth_date, ...) goes to the log only.
        current_app.logger.warning("telegram-webapp login rejected: %s", e)
        return fail("Invalid initData", 401, code="INVALID_INITDATA")

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

    token = create_session(u_id, device_key)

    # Foydalanuvchi ma'lumotlarini tekshirish
    user = fetch_one("SELECT u_phone FROM users WHERE u_id=%s", (u_id,))

    return ok({
        "session_token": token,
        "u_id": u_id,
        "is_registered": bool(user and user.get("u_phone"))
    })
