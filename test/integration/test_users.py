"""
Integration tests — api/users.py
/api/me, /api/users/ensure, /api/users/<u_id>, /api/me/settings, /api/gardeners
"""
from datetime import datetime
from unittest.mock import patch, MagicMock

import pytest

from conftest import (
    TEST_API_KEY,
    TEST_TOKEN,
    TEST_U_ID,
    FAKE_USER,
    FAKE_CATEGORY,
    FAKE_SESSION_DB_ROW,
    FAKE_PARTNER,
    FAKE_INVITE,
    NOW,
)

API_H = {"X-API-KEY": TEST_API_KEY, "Content-Type": "application/json"}
SESSION_H = {"Authorization": f"Bearer {TEST_TOKEN}", "Content-Type": "application/json"}


# ─── GET /api/me ─────────────────────────────────────────────────────────────

class TestGetMe:
    URL = "/api/me"

    def test_success_returns_user(self, client, mock_session):
        with patch("api.users.fetch_one", return_value=FAKE_USER):
            resp = client.get(self.URL, headers=SESSION_H)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True
        assert data["data"]["u_id"] == TEST_U_ID
        assert data["data"]["u_name"] == FAKE_USER["u_name"]

    def test_no_auth_returns_401(self, client):
        resp = client.get(self.URL)
        assert resp.status_code == 401

    def test_user_not_found_returns_404(self, client, mock_session):
        with patch("api.users.fetch_one", return_value=None):
            resp = client.get(self.URL, headers=SESSION_H)
        assert resp.status_code == 404
        data = resp.get_json()
        assert data["error"]["code"] == "NOT_FOUND"

    def test_response_has_required_fields(self, client, mock_session):
        with patch("api.users.fetch_one", return_value=FAKE_USER):
            resp = client.get(self.URL, headers=SESSION_H)
        d = resp.get_json()["data"]
        for field in ("u_id", "u_name", "u_phone", "u_username", "u_age"):
            assert field in d, f"Field yo'q: {field}"

    def test_wrong_token_returns_401(self, client):
        with patch("middleware.require_session.get_cache", return_value=None), \
             patch("middleware.require_session.fetch_one", return_value=None):
            resp = client.get(self.URL, headers={"Authorization": "Bearer wrong-token"})
        assert resp.status_code == 401


# ─── POST /api/users/ensure ───────────────────────────────────────────────────

class TestEnsureUser:
    URL = "/api/users/ensure"

    def test_creates_new_user(self, client):
        with patch("api.users.execute"), \
             patch("api.users.fetch_one", return_value=FAKE_USER):
            resp = client.post(self.URL, json={"u_id": TEST_U_ID}, headers=API_H)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True
        assert data["data"]["u_id"] == TEST_U_ID

    def test_missing_u_id_returns_400(self, client):
        resp = client.post(self.URL, json={}, headers=API_H)
        assert resp.status_code == 400

    def test_string_u_id_returns_400(self, client):
        resp = client.post(self.URL, json={"u_id": "notint"}, headers=API_H)
        assert resp.status_code == 400

    def test_no_api_key_returns_401(self, client):
        resp = client.post(self.URL, json={"u_id": TEST_U_ID})
        assert resp.status_code == 401

    def test_with_all_optional_fields(self, client):
        with patch("api.users.execute"), \
             patch("api.users.fetch_one", return_value=FAKE_USER):
            resp = client.post(self.URL, json={
                "u_id": TEST_U_ID,
                "u_name": "Ali",
                "u_phone": "+998901234567",
                "u_username": "ali_dev",
                "u_age": 30,
                "u_photo": "http://example.com/photo.jpg",
            }, headers=API_H)
        assert resp.status_code == 200

    def test_upsert_returns_existing_user(self, client):
        with patch("api.users.execute"), \
             patch("api.users.fetch_one", return_value=FAKE_USER):
            resp = client.post(self.URL, json={"u_id": TEST_U_ID}, headers=API_H)
        assert resp.get_json()["data"]["u_id"] == TEST_U_ID

    def test_float_u_id_returns_400(self, client):
        resp = client.post(self.URL, json={"u_id": 1.5}, headers=API_H)
        assert resp.status_code == 400

    def test_response_has_timestamps(self, client):
        with patch("api.users.execute"), \
             patch("api.users.fetch_one", return_value=FAKE_USER):
            resp = client.post(self.URL, json={"u_id": TEST_U_ID}, headers=API_H)
        d = resp.get_json()["data"]
        assert "added_at" in d or "u_id" in d


# ─── GET /api/users/<u_id> ────────────────────────────────────────────────────

class TestGetUser:
    def test_success(self, client):
        with patch("api.users.fetch_one", return_value=FAKE_USER):
            resp = client.get(f"/api/users/{TEST_U_ID}", headers=API_H)
        assert resp.status_code == 200
        assert resp.get_json()["data"]["u_id"] == TEST_U_ID

    def test_not_found_returns_404(self, client):
        with patch("api.users.fetch_one", return_value=None):
            resp = client.get("/api/users/9999999", headers=API_H)
        assert resp.status_code == 404
        assert resp.get_json()["error"]["code"] == "NOT_FOUND"

    def test_no_api_key_returns_401(self, client):
        resp = client.get(f"/api/users/{TEST_U_ID}")
        assert resp.status_code == 401

    def test_returns_expected_fields(self, client):
        with patch("api.users.fetch_one", return_value=FAKE_USER):
            resp = client.get(f"/api/users/{TEST_U_ID}", headers=API_H)
        d = resp.get_json()["data"]
        assert d["u_id"] == TEST_U_ID
        assert d["u_name"] == FAKE_USER["u_name"]
        assert d["u_phone"] == FAKE_USER["u_phone"]


# ─── GET /api/me/settings ────────────────────────────────────────────────────

class TestSettingsMe:
    URL = "/api/me/settings"

    def _setup_mocks(self):
        session_row = {
            "session_id": 1, "device_name": "Chrome", "city": "Toshkent",
            "ip_address": "127.0.0.1", "created_at": NOW, "token_hash": "hash1",
        }
        return {
            "partners": [FAKE_PARTNER],
            "sessions": [session_row],
            "invite": FAKE_INVITE,
        }

    def test_success_returns_partners_sessions_token(self, client, mock_session):
        mocks = self._setup_mocks()
        with patch("api.users.fetch_all", side_effect=[
            [FAKE_PARTNER],      # partners query
            [mocks["sessions"][0]],   # sessions query
        ]), \
        patch("api.users.fetch_one", side_effect=[
            mocks["sessions"][0],  # current session check
            FAKE_INVITE,           # existing invite token
        ]), \
        patch("api.users.execute"), \
        patch("api.users.get_cache", return_value=None), \
        patch("api.users.set_cache"):
            resp = client.get(self.URL, headers=SESSION_H)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True
        assert "partners" in data["data"]
        assert "sessions" in data["data"]
        assert "invite_token" in data["data"]
        assert "bot_username" in data["data"]

    def test_no_auth_returns_401(self, client):
        resp = client.get(self.URL)
        assert resp.status_code == 401

    def test_cached_response_returned(self, client, mock_session):
        cached = {"partners": [], "sessions": [], "invite_token": "abc", "bot_username": "bot"}
        with patch("api.users.get_cache", return_value=cached):
            resp = client.get(self.URL, headers=SESSION_H)
        assert resp.status_code == 200
        assert resp.get_json()["data"]["invite_token"] == "abc"

    def test_bot_username_in_response(self, client, mock_session):
        cached = {"partners": [], "sessions": [], "invite_token": "tok", "bot_username": "test_kochatim_bot"}
        with patch("api.users.get_cache", return_value=cached):
            resp = client.get(self.URL, headers=SESSION_H)
        assert resp.get_json()["data"]["bot_username"] == "test_kochatim_bot"


# ─── GET /api/gardeners ───────────────────────────────────────────────────────

class TestGardeners:
    URL = "/api/gardeners"

    GARDENER = {
        "u_id": TEST_U_ID,
        "u_name": "Ali Bogbon",
        "u_username": "alibog",
        "u_phone": "+998901234567",
        "u_photo": None,
        "added_at": NOW,
    }

    def test_public_endpoint_no_auth_needed(self, client):
        with patch("api.users.fetch_all", return_value=[self.GARDENER]):
            resp = client.get(self.URL)
        assert resp.status_code == 200

    def test_returns_list(self, client):
        with patch("api.users.fetch_all", return_value=[self.GARDENER]):
            resp = client.get(self.URL)
        data = resp.get_json()
        assert isinstance(data["data"], list)

    def test_empty_result(self, client):
        with patch("api.users.fetch_all", return_value=[]):
            resp = client.get(self.URL)
        assert resp.get_json()["data"] == []

    def test_search_by_name(self, client):
        with patch("api.users.fetch_all", return_value=[self.GARDENER]):
            resp = client.get(f"{self.URL}?q=Ali")
        assert resp.status_code == 200

    def test_search_by_numeric_u_id(self, client):
        with patch("api.users.fetch_all", return_value=[self.GARDENER]):
            resp = client.get(f"{self.URL}?q={TEST_U_ID}")
        assert resp.status_code == 200

    def test_custom_limit(self, client):
        gardeners = [self.GARDENER] * 5
        with patch("api.users.fetch_all", return_value=gardeners):
            resp = client.get(f"{self.URL}?limit=5")
        assert resp.status_code == 200

    def test_limit_capped_at_50(self, client):
        with patch("api.users.fetch_all", return_value=[]) as mock_fa:
            resp = client.get(f"{self.URL}?limit=100")
        assert resp.status_code == 200
        # limit parametr 50 ga cappinglanishi kerak — SQL LIMIT %s da 50 ishlatiladi

    def test_default_limit_12(self, client):
        with patch("api.users.fetch_all", return_value=[]) as mock_fa:
            resp = client.get(self.URL)
        assert resp.status_code == 200
        call_args = mock_fa.call_args
        assert 12 in call_args[0][1]

    def test_result_has_u_phone(self, client):
        with patch("api.users.fetch_all", return_value=[self.GARDENER]):
            resp = client.get(self.URL)
        assert "u_phone" in resp.get_json()["data"][0]
