"""
Unit tests — utils/security.py
Har bir funksiya alohida, izolyatsiyada testlanadi.
"""
import hashlib
import hmac
import json
import time

import pytest

# conftest.py backend yo'lini sys.path ga qo'shadi
from utils.security import (
    generate_invite_token,
    generate_otp_6,
    generate_token,
    parse_telegram_user,
    random_token,
    safe_equal,
    sha256_hex,
    telegram_webapp_verify,
)


# ─── sha256_hex ───────────────────────────────────────────────────────────────

class TestSha256Hex:
    def test_returns_hex_string(self):
        result = sha256_hex("hello")
        assert isinstance(result, str)
        assert all(c in "0123456789abcdef" for c in result)

    def test_correct_length(self):
        assert len(sha256_hex("test")) == 64

    def test_deterministic(self):
        assert sha256_hex("same") == sha256_hex("same")

    def test_different_inputs_different_hashes(self):
        assert sha256_hex("abc") != sha256_hex("def")

    def test_empty_string(self):
        result = sha256_hex("")
        assert len(result) == 64

    def test_known_value(self):
        expected = hashlib.sha256("hello".encode()).hexdigest()
        assert sha256_hex("hello") == expected

    def test_unicode_input(self):
        result = sha256_hex("ko'chat")
        assert len(result) == 64


# ─── generate_otp_6 ──────────────────────────────────────────────────────────

class TestGenerateOtp6:
    def test_returns_6_chars(self):
        assert len(generate_otp_6()) == 6

    def test_only_digits(self):
        for _ in range(20):
            code = generate_otp_6()
            assert code.isdigit(), f"OTP raqam emas: {code}"

    def test_different_each_time(self):
        codes = {generate_otp_6() for _ in range(50)}
        assert len(codes) > 1

    def test_range_zero_to_999999(self):
        for _ in range(30):
            val = int(generate_otp_6())
            assert 0 <= val <= 999999

    def test_leading_zeros_preserved(self):
        # 000001 kabi kodlar 6 ta belgili bo'lishi shart
        for _ in range(100):
            code = generate_otp_6()
            assert len(code) == 6


# ─── generate_token ───────────────────────────────────────────────────────────

class TestGenerateToken:
    def test_returns_string(self):
        assert isinstance(generate_token(32), str)

    def test_not_empty(self):
        assert len(generate_token(32)) > 0

    def test_url_safe_chars(self):
        token = generate_token(32)
        allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_=")
        assert all(c in allowed for c in token), f"URL-unsafe belgi: {token}"

    def test_different_each_time(self):
        tokens = {generate_token(32) for _ in range(20)}
        assert len(tokens) > 1

    def test_length_varies_with_bytes(self):
        short = generate_token(8)
        long_ = generate_token(64)
        assert len(long_) > len(short)


# ─── random_token ─────────────────────────────────────────────────────────────

class TestRandomToken:
    def test_returns_hex_string(self):
        t = random_token(32)
        assert all(c in "0123456789abcdef" for c in t)

    def test_length_is_double_nbytes(self):
        assert len(random_token(32)) == 64
        assert len(random_token(16)) == 32

    def test_different_each_time(self):
        tokens = {random_token(32) for _ in range(20)}
        assert len(tokens) > 1


# ─── generate_invite_token ────────────────────────────────────────────────────

class TestGenerateInviteToken:
    def test_returns_string(self):
        assert isinstance(generate_invite_token(), str)

    def test_no_special_chars(self):
        token = generate_invite_token()
        allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_=")
        assert all(c in allowed for c in token)

    def test_min_length(self):
        assert len(generate_invite_token()) >= 20

    def test_unique_tokens(self):
        tokens = {generate_invite_token() for _ in range(20)}
        assert len(tokens) > 1


# ─── safe_equal ───────────────────────────────────────────────────────────────

class TestSafeEqual:
    def test_equal_strings(self):
        assert safe_equal("abc", "abc") is True

    def test_unequal_strings(self):
        assert safe_equal("abc", "xyz") is False

    def test_empty_strings(self):
        assert safe_equal("", "") is True

    def test_different_lengths(self):
        assert safe_equal("ab", "abc") is False

    def test_unicode(self):
        assert safe_equal("ko'chat", "ko'chat") is True
        assert safe_equal("ko'chat", "ko'CHAT") is False


# ─── telegram_webapp_verify ───────────────────────────────────────────────────

class TestTelegramWebappVerify:

    def _build_init_data(self, bot_token: str, extra: dict = None) -> str:
        user_obj = json.dumps({"id": 1111, "first_name": "Ali"})
        pairs = {
            "user": user_obj,
            "auth_date": str(int(time.time())),
        }
        if extra:
            pairs.update(extra)
        data_check = "\n".join(f"{k}={pairs[k]}" for k in sorted(pairs.keys()))
        secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
        h = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
        pairs["hash"] = h
        return "&".join(f"{k}={v}" for k, v in pairs.items())

    def test_valid_init_data_returns_dict(self):
        token = "123456789:TESTTOKEN"
        init_data = self._build_init_data(token)
        result = telegram_webapp_verify(init_data, token)
        assert isinstance(result, dict)
        assert "user" in result
        assert "hash" not in result

    def test_wrong_bot_token_raises(self):
        token = "123456789:CORRECT"
        init_data = self._build_init_data(token)
        with pytest.raises(ValueError, match="invalid hash"):
            telegram_webapp_verify(init_data, "000000000:WRONG")

    def test_empty_init_data_raises(self):
        with pytest.raises(ValueError, match="initData missing"):
            telegram_webapp_verify("", "sometoken")

    def test_missing_hash_raises(self):
        with pytest.raises(ValueError, match="hash missing"):
            telegram_webapp_verify("user=test&auth_date=1234", "sometoken")

    def test_empty_bot_token_raises(self):
        with pytest.raises(ValueError, match="BOT_TOKEN missing"):
            telegram_webapp_verify("user=test&hash=abc", "")

    def test_tampered_data_raises(self):
        token = "123456789:TESTTOKEN"
        init_data = self._build_init_data(token)
        tampered = init_data.replace("Ali", "Hacker")
        with pytest.raises(ValueError, match="invalid hash"):
            telegram_webapp_verify(tampered, token)


# ─── parse_telegram_user ─────────────────────────────────────────────────────

class TestParseTelegramUser:
    def test_full_name(self):
        parsed = {"user": json.dumps({"id": 99, "first_name": "Rahim", "last_name": "Rahimov"})}
        result = parse_telegram_user(parsed)
        assert result["u_id"] == 99
        assert result["u_name"] == "Rahim Rahimov"
        assert result["u_username"] is None

    def test_first_name_only(self):
        parsed = {"user": json.dumps({"id": 88, "first_name": "Ali"})}
        result = parse_telegram_user(parsed)
        assert result["u_name"] == "Ali"

    def test_username_extracted(self):
        parsed = {"user": json.dumps({"id": 77, "first_name": "X", "username": "myuser"})}
        result = parse_telegram_user(parsed)
        assert result["u_username"] == "myuser"

    def test_no_username_returns_none(self):
        parsed = {"user": json.dumps({"id": 66, "first_name": "Y"})}
        result = parse_telegram_user(parsed)
        assert result["u_username"] is None

    def test_missing_user_raises(self):
        with pytest.raises((ValueError, KeyError)):
            parse_telegram_user({})

    def test_u_id_is_int(self):
        parsed = {"user": json.dumps({"id": 12345, "first_name": "Test"})}
        result = parse_telegram_user(parsed)
        assert isinstance(result["u_id"], int)
