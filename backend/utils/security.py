# backend/utils/security.py
import hashlib
import hmac
import secrets
import json
from urllib.parse import parse_qsl


def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def generate_token(length_bytes: int = 32) -> str:
    return secrets.token_urlsafe(length_bytes)


def generate_otp_6() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def safe_equal(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def telegram_webapp_verify(init_data: str, bot_token: str) -> dict:
    """
    Telegram Mini App initData verification.
    Return: parsed key-values dict (hash removed) if valid, else raise ValueError.
    """
    if not init_data:
        raise ValueError("initData missing")
    if not bot_token:
        raise ValueError("BOT_TOKEN missing")

    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = pairs.pop("hash", None)
    if not received_hash:
        raise ValueError("hash missing")

    data_check_string = "\n".join(f"{k}={pairs[k]}" for k in sorted(pairs.keys()))

    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()

    if not safe_equal(computed_hash, received_hash):
        raise ValueError("invalid hash")

    return pairs


def parse_telegram_user(parsed: dict) -> dict:
    """
    parsed['user'] usually JSON string.
    Return dict: {u_id, u_name, u_username}
    """
    user_raw = parsed.get("user")
    if not user_raw:
        raise ValueError("user missing in initData")

    u = json.loads(user_raw)
    u_id = int(u["id"])
    first = (u.get("first_name") or "").strip()
    last = (u.get("last_name") or "").strip()
    u_name = (first + " " + last).strip() if (first or last) else first
    u_username = (u.get("username") or "").strip() or None
    return {"u_id": u_id, "u_name": u_name, "u_username": u_username}