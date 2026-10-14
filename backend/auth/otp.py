# backend/auth/otp.py
from flask import request
from auth import auth_bp
from auth.session_service import DeviceKeyError, create_session, parse_device_key
from config import Config
from db import execute, execute_returning, fetch_one
from utils.errors import ok, fail
from utils.security import generate_otp_6, sha256_hex
from utils.time import utc_in_seconds, utcnow, naive_utc
from utils.device import get_client_ip
from utils import ratelimit
from middleware.require_api_key import require_api_key

# Wrong-code limits per 10 minutes. The per-IP limit stops one machine
# guessing; the global one bounds a botnet spreading its guesses over many
# IPs (6 digits is only 10^6 values and a code lives for two minutes).
_FAIL_WINDOW = 600
_FAIL_LIMIT_PER_IP = 5
_FAIL_LIMIT_GLOBAL = 500


def _new_unique_code(now):
    """
    A fresh code whose hash no other live code shares. verify-code finds a
    code by hash alone, so two users holding the same six digits at once
    would otherwise be logged into each other's account.
    """
    for _ in range(10):
        code = generate_otp_6()
        code_hash = sha256_hex(code)
        clash = fetch_one(
            "SELECT 1 AS taken FROM login_codes WHERE code_hash=%s AND used_at IS NULL AND expires_at > %s LIMIT 1",
            (code_hash, now),
        )
        if not clash:
            return code, code_hash
    raise RuntimeError("could not allocate a unique login code")


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

    now = naive_utc(utcnow())
    code, code_hash = _new_unique_code(now)
    expires_at = naive_utc(utc_in_seconds(Config.OTP_TTL_SECONDS))

    # Only the newest code works: retire this user's earlier unused ones.
    execute(
        "UPDATE login_codes SET used_at=%s WHERE u_id=%s AND used_at IS NULL",
        (now, u_id),
    )
    execute(
        "INSERT INTO login_codes (code_hash, u_id, expires_at) VALUES (%s, %s, %s)",
        (code_hash, u_id, expires_at),
    )

    return ok({"code": code, "expires_in": Config.OTP_TTL_SECONDS})


def _too_many(window: int):
    resp, status = fail("Too many attempts. Try again later.", 429, code="RATE_LIMITED")
    resp.headers["Retry-After"] = str(ratelimit.retry_after(window))
    return resp, status


@auth_bp.post("/verify-code")
def verify_code():
    """
    Website OTP kiritadi -> session_token oladi
    body: { code, device_key }   (device_key = the browser's public JWK)
    """
    data = request.get_json(silent=True) or {}
    code = data.get("code")
    code = code.strip() if isinstance(code, str) else ""

    if len(code) != 6 or (not code.isdigit()):
        return fail("Invalid code", 400, code="INVALID_CODE")

    # Checked before the code is touched, so a request without a key cannot
    # burn somebody's one-time code.
    try:
        device_key = parse_device_key(data.get("device_key"))
    except DeviceKeyError:
        return fail("device_key required", 400, code="DEVICE_KEY_REQUIRED")

    ip = get_client_ip(request) or "unknown"
    ip_fails = ratelimit.count("otp_fail_ip", ip, _FAIL_WINDOW)
    all_fails = ratelimit.count("otp_fail_all", "all", _FAIL_WINDOW)
    if ip_fails is None or all_fails is None:
        # Cannot count attempts, so cannot bound guessing: refuse. Users who
        # are already logged in are unaffected (sessions live in Postgres).
        return fail("Login temporarily unavailable", 503, code="UNAVAILABLE")
    if ip_fails >= _FAIL_LIMIT_PER_IP or all_fails >= _FAIL_LIMIT_GLOBAL:
        return _too_many(_FAIL_WINDOW)

    def _wrong(message, error_code):
        ratelimit.record("otp_fail_ip", ip, _FAIL_WINDOW)
        ratelimit.record("otp_fail_all", "all", _FAIL_WINDOW)
        return fail(message, 400, code=error_code)

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
        return _wrong("Code not found", "CODE_NOT_FOUND")

    now = naive_utc(utcnow())
    if row["used_at"] is not None:
        return _wrong("Code already used", "CODE_USED")
    if row["expires_at"] <= now:
        return _wrong("Code expired", "CODE_EXPIRED")

    # Spend the code in one statement. A SELECT-then-UPDATE would let two
    # parallel requests both see it unused and both get a session.
    spent = execute_returning(
        "UPDATE login_codes SET used_at=%s WHERE id=%s AND used_at IS NULL RETURNING u_id",
        (now, row["id"]),
    )
    if not spent:
        return _wrong("Code already used", "CODE_USED")

    token = create_session(int(spent["u_id"]), device_key)
    return ok({
        "session_token": token,
        "u_id": int(spent["u_id"]),
        "expires_in": Config.SESSION_TTL_SECONDS,
    })
