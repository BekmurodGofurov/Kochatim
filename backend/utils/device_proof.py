# backend/utils/device_proof.py
"""
Device-bound sessions (DPoP-style proof of possession).

At login the browser makes an ECDSA P-256 key pair with extractable=false:
the private half can sign but can never be read out, not even by page
script, and copying localStorage does not copy it. It sends us the public
half (a JWK) and we store it on the session. From then on every request
carries

    X-Session-Proof: v1.<ts_ms>.<nonce>.<signature>

where the signature covers  ts.nonce.METHOD.path?query.sha256(token)  and is
the 64-byte raw r||s that WebCrypto produces. A token pasted into another
browser has no key to sign with, so it is worthless on its own.

This module is pure -- no Flask, no Redis. Replay protection (remembering
nonces) lives in the caller.
"""
import base64
import hashlib
import json
import re
import time
from typing import Optional

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature

PROOF_VERSION = "v1"

_B64URL = re.compile(r"^[A-Za-z0-9_-]+$")
_NONCE = re.compile(r"^[A-Za-z0-9_-]{16,64}$")


class ProofError(Exception):
    """Raised with a short machine reason. The reason is logged, never returned."""


def _b64url_decode(value: str) -> bytes:
    if not value or not _B64URL.match(value):
        raise ValueError("not base64url")
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _coord(value) -> int:
    raw = _b64url_decode(value) if isinstance(value, str) else b""
    if len(raw) != 32:
        raise ValueError("coordinate must be 32 bytes")
    return int.from_bytes(raw, "big")


def normalize_public_jwk(jwk) -> str:
    """
    Validate a client-supplied public key and return its canonical JSON.

    Raises ValueError for anything that is not a P-256 public key on the
    curve -- including a JWK that still carries a private part ("d").
    """
    if not isinstance(jwk, dict):
        raise ValueError("device_key must be an object")
    if "d" in jwk:
        raise ValueError("device_key must be a public key")
    if jwk.get("kty") != "EC" or jwk.get("crv") != "P-256":
        raise ValueError("device_key must be EC P-256")
    x, y = _coord(jwk.get("x")), _coord(jwk.get("y"))
    # Raises ValueError when the point is not on the curve.
    ec.EllipticCurvePublicNumbers(x, y, ec.SECP256R1()).public_key()
    canonical = {"kty": "EC", "crv": "P-256", "x": jwk["x"], "y": jwk["y"]}
    return json.dumps(canonical, separators=(",", ":"), sort_keys=True)


def jwk_thumbprint(canonical_jwk: str) -> str:
    """RFC 7638 thumbprint: SHA-256 over the required members in lexical order."""
    jwk = json.loads(canonical_jwk)
    material = json.dumps(
        {"crv": jwk["crv"], "kty": jwk["kty"], "x": jwk["x"], "y": jwk["y"]},
        separators=(",", ":"), sort_keys=True,
    )
    return base64.urlsafe_b64encode(
        hashlib.sha256(material.encode("utf-8")).digest()
    ).decode("ascii").rstrip("=")


def _load_public_key(canonical_jwk: str):
    jwk = json.loads(canonical_jwk)
    return ec.EllipticCurvePublicNumbers(
        _coord(jwk["x"]), _coord(jwk["y"]), ec.SECP256R1()
    ).public_key()


def proof_message(ts: str, nonce: str, method: str, target: str, token: str) -> bytes:
    token_digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return f"{ts}.{nonce}.{method.upper()}.{target}.{token_digest}".encode("utf-8")


def verify_proof(
    header_value: Optional[str],
    *,
    method: str,
    target: str,
    token: str,
    public_jwk: str,
    max_skew_seconds: int,
    now_ms: Optional[int] = None,
) -> str:
    """
    Check one request's proof. Returns the nonce on success so the caller can
    refuse a second use; raises ProofError(reason) otherwise.

    `target` is the request path plus "?query" when there is a query string,
    byte for byte what the browser signed.
    """
    if not header_value:
        raise ProofError("missing")
    parts = header_value.split(".")
    if len(parts) != 4 or parts[0] != PROOF_VERSION:
        raise ProofError("malformed")
    _, ts, nonce, sig_b64 = parts
    if not ts.isdigit() or len(ts) > 15 or not _NONCE.match(nonce):
        raise ProofError("malformed")

    now = int(now_ms if now_ms is not None else time.time() * 1000)
    if abs(now - int(ts)) > max_skew_seconds * 1000:
        raise ProofError("stale")

    try:
        sig = _b64url_decode(sig_b64)
        if len(sig) != 64:
            raise ValueError("signature must be 64 bytes")
        der = encode_dss_signature(
            int.from_bytes(sig[:32], "big"), int.from_bytes(sig[32:], "big")
        )
        _load_public_key(public_jwk).verify(
            der,
            proof_message(ts, nonce, method, target, token),
            ec.ECDSA(hashes.SHA256()),
        )
    except InvalidSignature:
        raise ProofError("bad_signature")
    except (ValueError, KeyError, TypeError):
        raise ProofError("malformed")
    return nonce
