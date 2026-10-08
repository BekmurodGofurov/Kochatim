"""
Unit tests — utils/invite_tokens.py

HMAC bilan imzolangan hamkor taklif tokenlari. Bu modul xavfsizlik
chegarasi: buzilgan imzo, muddati o'tgan yoki boshqa turdagi token
QABUL QILINMASLIGI kerak.
"""
import base64
import json
import time
from unittest.mock import patch

import pytest

from utils.invite_tokens import (
    _b64url_decode,
    _b64url_encode,
    _sign,
    make_partner_invite_token,
    parse_partner_invite_token,
)

INVITER = 123456789


# ─── _b64url_encode / _b64url_decode ─────────────────────────────────────────

class TestB64Url:
    def test_roundtrip_bytes(self):
        raw = b"hello world"
        assert _b64url_decode(_b64url_encode(raw)) == raw

    def test_roundtrip_empty(self):
        assert _b64url_decode(_b64url_encode(b"")) == b""

    def test_encode_strips_padding(self):
        # "=" URL da muammo tug'diradi, shuning uchun olib tashlanadi
        assert "=" not in _b64url_encode(b"a")
        assert "=" not in _b64url_encode(b"ab")
        assert "=" not in _b64url_encode(b"abc")

    def test_decode_restores_padding(self):
        for n in range(1, 10):
            raw = b"x" * n
            assert _b64url_decode(_b64url_encode(raw)) == raw

    def test_url_safe_alphabet_only(self):
        # Standart base64 "+" va "/" beradi — URL uchun yaramaydi
        raw = bytes(range(256))
        encoded = _b64url_encode(raw)
        assert "+" not in encoded and "/" not in encoded

    def test_roundtrip_binary_payload(self):
        raw = bytes(range(256))
        assert _b64url_decode(_b64url_encode(raw)) == raw


# ─── _sign ────────────────────────────────────────────────────────────────────

class TestSign:
    def test_deterministic(self):
        assert _sign("payload") == _sign("payload")

    def test_different_payload_different_signature(self):
        assert _sign("payload-a") != _sign("payload-b")

    def test_returns_hex_sha256(self):
        sig = _sign("payload")
        assert len(sig) == 64
        int(sig, 16)  # hex bo'lishi kerak

    def test_signature_depends_on_api_key(self):
        with patch("utils.invite_tokens.Config.API_KEY", "key-one"):
            first = _sign("payload")
        with patch("utils.invite_tokens.Config.API_KEY", "key-two"):
            second = _sign("payload")
        assert first != second


# ─── make_partner_invite_token ───────────────────────────────────────────────

class TestMakeToken:
    def test_has_payload_and_signature(self):
        token = make_partner_invite_token(INVITER)
        assert token.count(".") == 1
        payload_b64, sig = token.split(".")
        assert payload_b64 and len(sig) == 64

    def test_payload_contains_inviter(self):
        token = make_partner_invite_token(INVITER)
        payload = json.loads(_b64url_decode(token.split(".")[0]))
        assert payload["inviter"] == INVITER

    def test_payload_type_and_version(self):
        token = make_partner_invite_token(INVITER)
        payload = json.loads(_b64url_decode(token.split(".")[0]))
        assert payload["type"] == "partner_invite"
        assert payload["v"] == 1

    def test_default_ttl_is_seven_days(self):
        token = make_partner_invite_token(INVITER)
        payload = json.loads(_b64url_decode(token.split(".")[0]))
        assert payload["exp"] - payload["iat"] == 7 * 24 * 3600

    def test_custom_ttl_respected(self):
        token = make_partner_invite_token(INVITER, ttl_seconds=60)
        payload = json.loads(_b64url_decode(token.split(".")[0]))
        assert payload["exp"] - payload["iat"] == 60

    def test_string_inviter_id_is_coerced_to_int(self):
        token = make_partner_invite_token("42")
        payload = json.loads(_b64url_decode(token.split(".")[0]))
        assert payload["inviter"] == 42

    def test_token_is_url_safe(self):
        token = make_partner_invite_token(INVITER)
        # Telegram deep-link ichida ishlatiladi — maxsus belgi bo'lmasligi kerak
        assert all(c.isalnum() or c in "-_." for c in token)

    def test_includes_a_nonce(self):
        token = make_partner_invite_token(INVITER)
        payload = json.loads(_b64url_decode(token.split(".")[0]))
        assert payload.get("nonce")


# ─── parse_partner_invite_token — muvaffaqiyatli yo'l ────────────────────────

class TestParseTokenSuccess:
    def test_roundtrip_returns_payload_and_no_error(self):
        token = make_partner_invite_token(INVITER)
        payload, err = parse_partner_invite_token(token)
        assert err is None
        assert payload["inviter"] == INVITER

    def test_accepts_token_valid_for_one_more_second(self):
        token = make_partner_invite_token(INVITER, ttl_seconds=10)
        payload, err = parse_partner_invite_token(token)
        assert err is None and payload is not None


# ─── parse_partner_invite_token — rad etish yo'llari ─────────────────────────

class TestParseTokenRejection:
    def test_missing_dot_is_invalid_format(self):
        payload, err = parse_partner_invite_token("no-dot-here")
        assert payload is None and err == "INVALID_FORMAT"

    def test_empty_string_is_invalid_format(self):
        payload, err = parse_partner_invite_token("")
        assert payload is None and err == "INVALID_FORMAT"

    def test_tampered_signature_is_rejected(self):
        token = make_partner_invite_token(INVITER)
        payload_b64, _sig = token.split(".")
        payload, err = parse_partner_invite_token(f"{payload_b64}.{'0' * 64}")
        assert payload is None and err == "INVALID_SIGNATURE"

    def test_tampered_payload_is_rejected(self):
        """Inviter ni boshqa odamga o'zgartirish imzoni buzishi kerak."""
        token = make_partner_invite_token(INVITER)
        _payload_b64, sig = token.split(".")
        evil = json.dumps({
            "v": 1, "type": "partner_invite", "inviter": 999,
            "iat": int(time.time()), "exp": int(time.time()) + 3600, "nonce": "x",
        }, separators=(",", ":"))
        forged = f"{_b64url_encode(evil.encode())}.{sig}"
        payload, err = parse_partner_invite_token(forged)
        assert payload is None and err == "INVALID_SIGNATURE"

    def test_expired_token_is_rejected(self):
        token = make_partner_invite_token(INVITER, ttl_seconds=-10)
        payload, err = parse_partner_invite_token(token)
        assert payload is None and err == "EXPIRED"

    def test_wrong_type_is_rejected(self):
        """Boshqa maqsadda imzolangan token hamkor taklifi sifatida o'tmasligi kerak."""
        body = json.dumps({
            "v": 1, "type": "password_reset", "inviter": INVITER,
            "iat": int(time.time()), "exp": int(time.time()) + 3600,
        }, separators=(",", ":"))
        payload_b64 = _b64url_encode(body.encode())
        token = f"{payload_b64}.{_sign(payload_b64)}"
        payload, err = parse_partner_invite_token(token)
        assert payload is None and err == "WRONG_TYPE"

    def test_non_json_payload_is_invalid_format(self):
        payload_b64 = _b64url_encode(b"this is not json")
        token = f"{payload_b64}.{_sign(payload_b64)}"
        payload, err = parse_partner_invite_token(token)
        assert payload is None and err == "INVALID_FORMAT"

    def test_undecodable_payload_is_invalid_format(self):
        payload_b64 = "!!!not-base64!!!"
        token = f"{payload_b64}.{_sign(payload_b64)}"
        payload, err = parse_partner_invite_token(token)
        assert payload is None and err == "INVALID_FORMAT"

    def test_fails_closed_without_api_key(self):
        """
        Sir bo'lmasa imzoni tekshirib bo'lmaydi — token QABUL QILINMASLIGI
        kerak, aks holda har qanday satr amal qiluvchi taklif bo'lib qoladi.
        """
        token = make_partner_invite_token(INVITER)
        with patch("utils.invite_tokens.Config.API_KEY", ""):
            payload, err = parse_partner_invite_token(token)
        assert payload is None and err == "INVALID_SIGNATURE"

    def test_token_from_another_secret_is_rejected(self):
        with patch("utils.invite_tokens.Config.API_KEY", "attacker-key"):
            token = make_partner_invite_token(INVITER)
        # Haqiqiy sir bilan tekshirilganda o'tmasligi kerak
        payload, err = parse_partner_invite_token(token)
        assert payload is None and err == "INVALID_SIGNATURE"

    def test_signature_comparison_is_constant_time(self):
        """hmac.compare_digest ishlatilgani timing hujumini qiyinlashtiradi."""
        import utils.invite_tokens as mod
        import inspect

        src = inspect.getsource(mod.parse_partner_invite_token)
        assert "compare_digest" in src

    def test_missing_exp_is_accepted(self):
        # exp yo'q bo'lsa muddat tekshiruvi o'tkazib yuboriladi (hujjatlashtirilgan xatti-harakat)
        body = json.dumps({
            "v": 1, "type": "partner_invite", "inviter": INVITER,
        }, separators=(",", ":"))
        payload_b64 = _b64url_encode(body.encode())
        token = f"{payload_b64}.{_sign(payload_b64)}"
        payload, err = parse_partner_invite_token(token)
        assert err is None and payload["inviter"] == INVITER
