import base64
import hashlib
import hmac
import json
import time
from typing import Any, Dict, Optional, Tuple

from config import Config


def _b64url_encode(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode("utf-8").rstrip("=")


def _b64url_decode(s: str) -> bytes:
    pad = "=" * ((4 - len(s) % 4) % 4)
    return base64.urlsafe_b64decode((s + pad).encode("utf-8"))


def _sign(payload_b64: str) -> str:
    secret = (Config.API_KEY or "").encode("utf-8")
    return hmac.new(secret, payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()


def make_partner_invite_token(inviter_u_id: int, ttl_seconds: int = 7 * 24 * 3600) -> str:
    now = int(time.time())
    payload: Dict[str, Any] = {
        "v": 1,
        "type": "partner_invite",
        "inviter": int(inviter_u_id),
        "iat": now,
        "exp": now + int(ttl_seconds),
        "nonce": _b64url_encode(hashlib.sha256(f"{inviter_u_id}:{now}".encode("utf-8")).digest()[:9]),
    }
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    sig = _sign(payload_b64)
    return f"{payload_b64}.{sig}"


def parse_partner_invite_token(token: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Returns (payload, error_code)
    error_code in: INVALID_FORMAT, INVALID_SIGNATURE, EXPIRED, WRONG_TYPE
    """
    try:
        payload_b64, sig = token.split(".", 1)
    except Exception:
        return None, "INVALID_FORMAT"

    if not Config.API_KEY:
        # Without a secret, invites are unsafe; fail closed.
        return None, "INVALID_SIGNATURE"

    expected_sig = _sign(payload_b64)
    if not hmac.compare_digest(expected_sig, sig):
        return None, "INVALID_SIGNATURE"

    try:
        payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
    except Exception:
        return None, "INVALID_FORMAT"

    if payload.get("type") != "partner_invite":
        return None, "WRONG_TYPE"

    exp = payload.get("exp")
    if isinstance(exp, (int, float)) and int(exp) < int(time.time()):
        return None, "EXPIRED"

    return payload, None

