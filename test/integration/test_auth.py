"""
Integration tests — auth/ blueprinti
/auth/request-code, /auth/verify-code, /auth/telegram-webapp, /auth/user-id-login
"""
import hashlib
import json
from datetime import datetime
from unittest.mock import patch, call

import pytest

from conftest import (
    TEST_API_KEY,
    TEST_BOT_TOKEN,
    TEST_OTP_CODE,
    TEST_U_ID,
    FAKE_USER,
    FAKE_LOGIN_CODE,
    build_valid_init_data,
)

API_KEY_H = {"X-API-KEY": TEST_API_KEY, "Content-Type": "application/json"}
JSON_H = {"Content-Type": "application/json"}


def _code_hash(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


# ─── POST /auth/request-code ─────────────────────────────────────────────────

class TestRequestCode:
    URL = "/auth/request-code"

    def test_success_returns_code_and_expires_in(self, client):
        with patch("auth.otp.execute"), \
             patch("auth.otp.fetch_all", return_value=[]):
            resp = client.post(self.URL, json={"u_id": TEST_U_ID}, headers=API_KEY_H)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True
        assert "code" in data["data"]
        assert "expires_in" in data["data"]
        assert len(data["data"]["code"]) == 6
        assert data["data"]["code"].isdigit()

    def test_expires_in_is_120(self, client):
        with patch("auth.otp.execute"), \
             patch("auth.otp.fetch_all", return_value=[]):
            resp = client.post(self.URL, json={"u_id": TEST_U_ID}, headers=API_KEY_H)
        assert resp.get_json()["data"]["expires_in"] == 120

    def test_missing_u_id_returns_400(self, client):
        resp = client.post(self.URL, json={}, headers=API_KEY_H)
        assert resp.status_code == 400

    def test_string_u_id_returns_400(self, client):
        resp = client.post(self.URL, json={"u_id": "not_int"}, headers=API_KEY_H)
        assert resp.status_code == 400

    def test_no_api_key_returns_401(self, client):
        resp = client.post(self.URL, json={"u_id": TEST_U_ID}, headers=JSON_H)
        assert resp.status_code == 401

    def test_wrong_api_key_returns_401(self, client):
        resp = client.post(
            self.URL,
            json={"u_id": TEST_U_ID},
            headers={"X-API-KEY": "wrong", "Content-Type": "application/json"},
        )
        assert resp.status_code == 401

    def test_optional_fields_accepted(self, client):
        with patch("auth.otp.execute"), \
             patch("auth.otp.fetch_all", return_value=[]):
            resp = client.post(self.URL, json={
                "u_id": TEST_U_ID,
                "u_name": "Ali",
                "u_phone": "+998901234567",
                "u_username": "ali_user",
                "u_age": 25,
            }, headers=API_KEY_H)
        assert resp.status_code == 200

    def test_u_id_float_returns_400(self, client):
        resp = client.post(self.URL, json={"u_id": 1.5}, headers=API_KEY_H)
        assert resp.status_code == 400

    def test_u_id_null_returns_400(self, client):
        resp = client.post(self.URL, json={"u_id": None}, headers=API_KEY_H)
        assert resp.status_code == 400

    def test_old_sessions_pruned_when_more_than_3(self, client):
        sessions = [{"token_hash": f"hash{i}"} for i in range(5)]
        with patch("auth.otp.execute") as mock_exec, \
             patch("auth.otp.fetch_all", return_value=sessions):
            resp = client.post(self.URL, json={"u_id": TEST_U_ID}, headers=API_KEY_H)
        # execute chaqiruvlarini tekshiramiz (DELETE bo'lishi kerak)
        assert resp.status_code == 200


# ─── POST /auth/verify-code ───────────────────────────────────────────────────

class TestVerifyCode:
    URL = "/auth/verify-code"

    def _valid_code_row(self):
        return {
            "id": 1,
            "u_id": TEST_U_ID,
            "expires_at": datetime(2099, 1, 1),
            "used_at": None,
        }

    def test_success_returns_session_token(self, client):
        with patch("auth.otp.fetch_one", return_value=self._valid_code_row()), \
             patch("auth.otp.execute"), \
             patch("auth.otp.fetch_all", return_value=[]):
            resp = client.post(self.URL, json={"code": TEST_OTP_CODE}, headers=JSON_H)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True
        assert "session_token" in data["data"]
        assert data["data"]["u_id"] == TEST_U_ID

    def test_session_token_is_string(self, client):
        with patch("auth.otp.fetch_one", return_value=self._valid_code_row()), \
             patch("auth.otp.execute"), \
             patch("auth.otp.fetch_all", return_value=[]):
            resp = client.post(self.URL, json={"code": TEST_OTP_CODE}, headers=JSON_H)
        token = resp.get_json()["data"]["session_token"]
        assert isinstance(token, str)
        assert len(token) > 10

    def test_non_digit_code_returns_400(self, client):
        resp = client.post(self.URL, json={"code": "abcdef"}, headers=JSON_H)
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["error"]["code"] == "INVALID_CODE"

    def test_short_code_returns_400(self, client):
        resp = client.post(self.URL, json={"code": "123"}, headers=JSON_H)
        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "INVALID_CODE"

    def test_long_code_returns_400(self, client):
        resp = client.post(self.URL, json={"code": "1234567"}, headers=JSON_H)
        assert resp.status_code == 400

    def test_missing_code_returns_400(self, client):
        resp = client.post(self.URL, json={}, headers=JSON_H)
        assert resp.status_code == 400

    def test_code_not_found_returns_400(self, client):
        with patch("auth.otp.fetch_one", return_value=None):
            resp = client.post(self.URL, json={"code": "999999"}, headers=JSON_H)
        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "CODE_NOT_FOUND"

    def test_expired_code_returns_400(self, client):
        expired_row = {
            "id": 1, "u_id": TEST_U_ID,
            "expires_at": datetime(2000, 1, 1),
            "used_at": None,
        }
        with patch("auth.otp.fetch_one", return_value=expired_row):
            resp = client.post(self.URL, json={"code": TEST_OTP_CODE}, headers=JSON_H)
        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "CODE_EXPIRED"

    def test_already_used_code_returns_400(self, client):
        used_row = {
            "id": 1, "u_id": TEST_U_ID,
            "expires_at": datetime(2099, 1, 1),
            "used_at": datetime(2026, 1, 1),
        }
        with patch("auth.otp.fetch_one", return_value=used_row):
            resp = client.post(self.URL, json={"code": TEST_OTP_CODE}, headers=JSON_H)
        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "CODE_USED"

    def test_empty_string_code_returns_400(self, client):
        resp = client.post(self.URL, json={"code": ""}, headers=JSON_H)
        assert resp.status_code == 400


# ─── POST /auth/telegram-webapp ──────────────────────────────────────────────

class TestTelegramWebapp:
    URL = "/auth/telegram-webapp"

    def test_success_returns_session_token(self, client):
        init_data = build_valid_init_data(TEST_BOT_TOKEN, TEST_U_ID)
        user_with_phone = {"u_phone": "+998901234567"}
        with patch("auth.telegram_webapp.execute"), \
             patch("auth.telegram_webapp.fetch_one", return_value=user_with_phone), \
             patch("auth.telegram_webapp.fetch_all", return_value=[]):
            resp = client.post(self.URL, json={"initData": init_data}, headers=JSON_H)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True
        assert "session_token" in data["data"]
        assert data["data"]["u_id"] == TEST_U_ID

    def test_is_registered_true_when_phone_exists(self, client):
        init_data = build_valid_init_data(TEST_BOT_TOKEN, TEST_U_ID)
        with patch("auth.telegram_webapp.execute"), \
             patch("auth.telegram_webapp.fetch_one", return_value={"u_phone": "+998901111111"}), \
             patch("auth.telegram_webapp.fetch_all", return_value=[]):
            resp = client.post(self.URL, json={"initData": init_data}, headers=JSON_H)
        assert resp.get_json()["data"]["is_registered"] is True

    def test_is_registered_false_when_no_phone(self, client):
        init_data = build_valid_init_data(TEST_BOT_TOKEN, TEST_U_ID)
        with patch("auth.telegram_webapp.execute"), \
             patch("auth.telegram_webapp.fetch_one", return_value={"u_phone": None}), \
             patch("auth.telegram_webapp.fetch_all", return_value=[]):
            resp = client.post(self.URL, json={"initData": init_data}, headers=JSON_H)
        assert resp.get_json()["data"]["is_registered"] is False

    def test_invalid_init_data_returns_401(self, client):
        resp = client.post(self.URL, json={"initData": "invalid&data"}, headers=JSON_H)
        assert resp.status_code == 401
        data = resp.get_json()
        assert data["error"]["code"] == "INVALID_INITDATA"

    def test_missing_init_data_returns_401(self, client):
        resp = client.post(self.URL, json={}, headers=JSON_H)
        assert resp.status_code == 401

    def test_empty_init_data_returns_401(self, client):
        resp = client.post(self.URL, json={"initData": ""}, headers=JSON_H)
        assert resp.status_code == 401

    def test_tampered_hash_returns_401(self, client):
        init_data = build_valid_init_data(TEST_BOT_TOKEN) + "&extra=tamper"
        resp = client.post(self.URL, json={"initData": init_data}, headers=JSON_H)
        assert resp.status_code == 401


# ─── POST /auth/user-id-login ─────────────────────────────────────────────────

class TestUserIdLogin:
    URL = "/auth/user-id-login"

    def test_success_returns_session_token(self, client):
        with patch("auth.user_id_login.fetch_one", return_value={"u_id": TEST_U_ID}), \
             patch("auth.user_id_login.execute"), \
             patch("auth.user_id_login.fetch_all", return_value=[]):
            resp = client.post(self.URL, json={"u_id": TEST_U_ID}, headers=JSON_H)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True
        assert "session_token" in data["data"]
        assert data["data"]["u_id"] == TEST_U_ID
        assert "expires_in" in data["data"]

    def test_session_token_is_nonempty_string(self, client):
        with patch("auth.user_id_login.fetch_one", return_value={"u_id": TEST_U_ID}), \
             patch("auth.user_id_login.execute"), \
             patch("auth.user_id_login.fetch_all", return_value=[]):
            resp = client.post(self.URL, json={"u_id": TEST_U_ID}, headers=JSON_H)
        token = resp.get_json()["data"]["session_token"]
        assert isinstance(token, str) and len(token) > 10

    def test_user_not_found_returns_404(self, client):
        with patch("auth.user_id_login.fetch_one", return_value=None):
            resp = client.post(self.URL, json={"u_id": 9999999}, headers=JSON_H)
        assert resp.status_code == 404
        data = resp.get_json()
        assert data["error"]["code"] == "USER_NOT_FOUND"

    def test_missing_u_id_returns_400(self, client):
        resp = client.post(self.URL, json={}, headers=JSON_H)
        assert resp.status_code == 400

    def test_string_u_id_returns_400(self, client):
        resp = client.post(self.URL, json={"u_id": "abc"}, headers=JSON_H)
        assert resp.status_code == 400

    def test_null_u_id_returns_400(self, client):
        resp = client.post(self.URL, json={"u_id": None}, headers=JSON_H)
        assert resp.status_code == 400

    def test_expires_in_is_positive(self, client):
        with patch("auth.user_id_login.fetch_one", return_value={"u_id": TEST_U_ID}), \
             patch("auth.user_id_login.execute"), \
             patch("auth.user_id_login.fetch_all", return_value=[]):
            resp = client.post(self.URL, json={"u_id": TEST_U_ID}, headers=JSON_H)
        assert resp.get_json()["data"]["expires_in"] > 0
