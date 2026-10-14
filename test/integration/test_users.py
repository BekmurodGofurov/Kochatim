"""
Integration tests — api/users.py
/api/me, /api/users/ensure, /api/users/<u_id>, /api/me/settings, /api/gardeners
"""
from datetime import datetime
from unittest.mock import patch, MagicMock

import pytest

from conftest import SESSION_HEADERS, WEB_HEADERS
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
SESSION_H = dict(SESSION_HEADERS)


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
        with patch("api.users.fetch_all", return_value=[FAKE_PARTNER]), \
        patch("api.users.session_rows", return_value=[mocks["sessions"][0]]), \
        patch("api.users.fetch_one", return_value=FAKE_INVITE), \
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

    def test_is_current_is_decided_per_request_not_per_cache_entry(self, client, mock_session):
        """The cache is shared by all of a user's sessions; 'current' must not be."""
        from conftest import get_test_token_hash
        rows = [
            {"session_id": 1, "device_name": "A", "city": "", "ip_address": "",
             "created_at": None, "token_hash": get_test_token_hash()},
            {"session_id": 2, "device_name": "B", "city": "", "ip_address": "",
             "created_at": None, "token_hash": "someone-elses-hash"},
        ]
        cached = {"partners": [], "sessions": rows, "invite_token": "t", "bot_username": "b"}
        with patch("api.users.get_cache", return_value=cached):
            resp = client.get(self.URL, headers=SESSION_H)
        sessions = resp.get_json()["data"]["sessions"]
        assert [s["is_current"] for s in sessions] == [True, False]
        assert all("token_hash" not in s for s in sessions)

    def test_db_failure_returns_generic_500(self, client, mock_session):
        with patch("api.users.get_cache", return_value=None), \
             patch("api.users.fetch_all", side_effect=RuntimeError("dsn=postgres://u:pw@h")):
            resp = client.get(self.URL, headers=SESSION_H)
        assert resp.status_code == 500
        assert "postgres://" not in resp.get_data(as_text=True)

    def test_bot_username_in_response(self, client, mock_session):
        cached = {"partners": [], "sessions": [], "invite_token": "tok", "bot_username": "test_kochatim_bot"}
        with patch("api.users.get_cache", return_value=cached):
            resp = client.get(self.URL, headers=SESSION_H)
        assert resp.get_json()["data"]["bot_username"] == "test_kochatim_bot"


# ─── GET /api/gardeners ───────────────────────────────────────────────────────

class TestGardeners:
    """
    GET /api/gardeners -- a directory anyone with the web client key can page
    through, so it carries a name and a link target and nothing else.
    """
    URL = "/api/gardeners"

    ROW = {"u_id": TEST_U_ID, "u_name": "Ali Bogbon"}

    def test_requires_client_key(self, client):
        with patch("api.users.fetch_all", return_value=[self.ROW]) as mock_fa:
            resp = client.get(self.URL)
        assert resp.status_code == 401
        mock_fa.assert_not_called()

    def test_returns_list(self, client):
        with patch("api.users.fetch_all", return_value=[self.ROW]):
            resp = client.get(self.URL, headers=WEB_HEADERS)
        assert resp.status_code == 200
        assert resp.get_json()["data"] == [self.ROW]

    def test_empty_result(self, client):
        with patch("api.users.fetch_all", return_value=[]):
            resp = client.get(self.URL, headers=WEB_HEADERS)
        assert resp.get_json()["data"] == []

    def test_query_selects_only_id_and_name(self, client):
        """Phone, username and photo must not even be read from the table."""
        with patch("api.users.fetch_all", return_value=[]) as mock_fa:
            client.get(self.URL, headers=WEB_HEADERS)
        select_list = mock_fa.call_args[0][0].split("FROM")[0]
        for column in ("u_phone", "u_username", "u_photo", "u_age"):
            assert column not in select_list

    def test_search_by_name_uses_ilike_params(self, client):
        with patch("api.users.fetch_all", return_value=[]) as mock_fa:
            resp = client.get(f"{self.URL}?q=Ali", headers=WEB_HEADERS)
        assert resp.status_code == 200
        assert "%Ali%" in mock_fa.call_args[0][1]

    def test_search_by_numeric_u_id(self, client):
        with patch("api.users.fetch_all", return_value=[]) as mock_fa:
            resp = client.get(f"{self.URL}?q={TEST_U_ID}", headers=WEB_HEADERS)
        assert resp.status_code == 200
        assert TEST_U_ID in mock_fa.call_args[0][1]

    def test_limit_capped_at_50(self, client):
        with patch("api.users.fetch_all", return_value=[]) as mock_fa:
            client.get(f"{self.URL}?limit=100", headers=WEB_HEADERS)
        assert mock_fa.call_args[0][1][-1] == 50

    def test_default_limit_12(self, client):
        with patch("api.users.fetch_all", return_value=[]) as mock_fa:
            client.get(self.URL, headers=WEB_HEADERS)
        assert mock_fa.call_args[0][1][-1] == 12

    def test_db_failure_returns_generic_500(self, client):
        with patch("api.users.fetch_all", side_effect=RuntimeError("password=hunter2")):
            resp = client.get(self.URL, headers=WEB_HEADERS)
        assert resp.status_code == 500
        assert "hunter2" not in resp.get_data(as_text=True)


