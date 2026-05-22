# backend/auth/otp.py
from flask import request
from auth import auth_bp
from config import Config
from db import execute, fetch_one, fetch_all
from utils.errors import ok, fail
from utils.security import generate_otp_6, sha256_hex, generate_token
from utils.time import utc_in_seconds, utcnow, naive_utc
from utils.device import parse_device, get_city, get_client_ip
from middleware.require_api_key import require_api_key

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


@auth_bp.post("/request-code")
@require_api_key
def request_code():
    """
    Bot chaqiradi (X-API-KEY header talab qilinadi).
    body: { u_id, u_name, u_username?, u_phone?, u_age? }
    return: { code, expires_in }
    """
    data = request.get_json(silent=True) or {}
    u_id = data.get("u_id")
    if not isinstance(u_id, int):
        return fail("u_id(int) required", 400)

    u_name = (data.get("u_name") or "").strip() or None
    u_phone = (data.get("u_phone") or "").strip() or None
    u_username = (data.get("u_username") or "").strip() or None
    u_age = data.get("u_age")
    if u_age is not None:
        try:
            u_age = int(u_age)
        except Exception:
            u_age = None

    # ensure user exists (UPSERT)
    execute("""
    INSERT INTO users (u_id, u_name, u_phone, u_username, u_age)
    VALUES (%s, %s, %s, %s, %s)
    ON CONFLICT (u_id) DO UPDATE SET
        u_name = COALESCE(EXCLUDED.u_name, users.u_name),
        u_phone = COALESCE(EXCLUDED.u_phone, users.u_phone),
        u_username = COALESCE(EXCLUDED.u_username, users.u_username),
        u_age = COALESCE(EXCLUDED.u_age, users.u_age)
    """, (u_id, u_name, u_phone, u_username, u_age))

    code = generate_otp_6()
    code_hash = sha256_hex(code)
    expires_at = naive_utc(utc_in_seconds(Config.OTP_TTL_SECONDS))

    execute(
        "INSERT INTO login_codes (code_hash, u_id, expires_at) VALUES (%s, %s, %s)",
        (code_hash, u_id, expires_at),
    )

    return ok({"code": code, "expires_in": Config.OTP_TTL_SECONDS})


@auth_bp.post("/verify-code")
def verify_code():
    """
    Website OTP kiritadi -> session_token oladi
    body: { code }
    """
    data = request.get_json(silent=True) or {}
    code = (data.get("code") or "").strip()

    if len(code) != 6 or (not code.isdigit()):
        return fail("Invalid code", 400, code="INVALID_CODE")

    code_hash = sha256_hex(code)
    row = fetch_one(
        """
        SELECT id, u_id, expires_at, used_at
        FROM login_codes
        WHERE code_hash=%s
        ORDER BY id DESC
        LIMIT 1
        """,
        (code_hash,),
    )
    if not row:
        return fail("Code not found", 400, code="CODE_NOT_FOUND")

    now = naive_utc(utcnow())
    if row["used_at"] is not None:
        return fail("Code already used", 400, code="CODE_USED")
    if row["expires_at"] <= now:
        return fail("Code expired", 400, code="CODE_EXPIRED")

    # mark used
    execute("UPDATE login_codes SET used_at=%s WHERE id=%s", (now, row["id"]))

    # create session
    token = generate_token(32)
    token_hash = sha256_hex(token)
    expires_at = naive_utc(utc_in_seconds(Config.SESSION_TTL_SECONDS))

    ua = request.headers.get("User-Agent", "")
    ip = get_client_ip(request)
    _insert_session(token_hash, row["u_id"], expires_at, ua, ip)

    return ok({"session_token": token, "u_id": int(row["u_id"])})