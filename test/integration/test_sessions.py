"""
Integration tests — api/sessions.py
Sessiyalar ro'yxati va o'chirish endpointlari.
"""
from unittest.mock import patch

import pytest

from conftest import TEST_TOKEN, TEST_U_ID, FAKE_SESSION_DB_ROW, NOW
from conftest import SESSION_HEADERS, WEB_HEADERS

SESSION_H = dict(SESSION_HEADERS)


# ─── GET /api/sessions ────────────────────────────────────────────────────────

class TestListSessions:
    URL = "/api/sessions"

    def _session_row(self, is_current=True):
        from utils.security import sha256_hex
        return {
            "session_id": 1,
            "device_name": "Chrome macOS",
            "city": "Toshkent",
            "ip_address": "127.0.0.1",
            "created_at": NOW,
            "token_hash": sha256_hex(TEST_TOKEN) if is_current else "otherhash",
        }

    def test_success_returns_list(self, client, mock_session):
        row = self._session_row()
        with patch("api.sessions.fetch_one", return_value={"device_name": "Chrome"}), \
             patch("api.sessions.get_cache", return_value=None), \
             patch("api.sessions.fetch_all", return_value=[row]), \
             patch("api.sessions.set_cache"):
            resp = client.get(self.URL, headers=SESSION_H)
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert isinstance(data, list)
        assert len(data) == 1

    def test_session_has_required_fields(self, client, mock_session):
        row = self._session_row()
        with patch("api.sessions.fetch_one", return_value={"device_name": "Chrome"}), \
             patch("api.sessions.get_cache", return_value=None), \
             patch("api.sessions.fetch_all", return_value=[row]), \
             patch("api.sessions.set_cache"):
            resp = client.get(self.URL, headers=SESSION_H)
        item = resp.get_json()["data"][0]
        for field in ("session_id", "device_name", "city", "ip_address", "is_current"):
            assert field in item, f"Field yo'q: {field}"

    def test_current_session_marked(self, client, mock_session):
        from utils.security import sha256_hex
        current_hash = sha256_hex(TEST_TOKEN)
        row = {
            "session_id": 1,
            "device_name": "Chrome",
            "city": "Toshkent",
            "ip_address": "127.0.0.1",
            "created_at": NOW,
            "token_hash": current_hash,
        }
        with patch("api.sessions.fetch_one", return_value={"device_name": "Chrome"}), \
             patch("api.sessions.get_cache", return_value=None), \
             patch("api.sessions.fetch_all", return_value=[row]), \
             patch("api.sessions.set_cache"):
            resp = client.get(self.URL, headers=SESSION_H)
        assert resp.get_json()["data"][0]["is_current"] is True

    def test_other_session_not_marked_current(self, client, mock_session):
        row = self._session_row(is_current=False)
        with patch("api.sessions.fetch_one", return_value={"device_name": "Chrome"}), \
             patch("api.sessions.get_cache", return_value=None), \
             patch("api.sessions.fetch_all", return_value=[row]), \
             patch("api.sessions.set_cache"):
            resp = client.get(self.URL, headers=SESSION_H)
        assert resp.get_json()["data"][0]["is_current"] is False

    def test_cached_result_returned(self, client, mock_session):
        cached = [{"session_id": 1, "device_name": "Firefox", "city": "",
                   "ip_address": "", "created_at": None, "token_hash": "h"}]
        with patch("api.sessions.get_cache", return_value=cached), \
             patch("api.sessions.fetch_all") as mock_fa:
            resp = client.get(self.URL, headers=SESSION_H)
        assert resp.status_code == 200
        assert resp.get_json()["data"][0]["device_name"] == "Firefox"
        mock_fa.assert_not_called()

    def test_is_current_is_decided_per_request_not_per_cache_entry(self, client, mock_session):
        """One cache entry serves all of a user's sessions; 'current' must not be baked in."""
        from utils.security import sha256_hex
        cached = [
            {"session_id": 1, "device_name": "A", "city": "", "ip_address": "",
             "created_at": None, "token_hash": sha256_hex(TEST_TOKEN)},
            {"session_id": 2, "device_name": "B", "city": "", "ip_address": "",
             "created_at": None, "token_hash": "someone-elses-hash"},
        ]
        with patch("api.sessions.get_cache", return_value=cached):
            data = client.get(self.URL, headers=SESSION_H).get_json()["data"]
        assert [s["is_current"] for s in data] == [True, False]

    def test_token_hash_never_leaves_the_server(self, client, mock_session):
        row = self._session_row()
        with patch("api.sessions.get_cache", return_value=None), \
             patch("api.sessions.fetch_all", return_value=[row]), \
             patch("api.sessions.set_cache"):
            resp = client.get(self.URL, headers=SESSION_H)
        assert "token_hash" not in resp.get_json()["data"][0]
        assert row["token_hash"] not in resp.get_data(as_text=True)

    def test_db_failure_returns_generic_500(self, client, mock_session):
        with patch("api.sessions.get_cache", return_value=None), \
             patch("api.sessions.fetch_all", side_effect=RuntimeError("dsn=postgres://u:pw@h")):
            resp = client.get(self.URL, headers=SESSION_H)
        assert resp.status_code == 500
        assert "postgres://" not in resp.get_data(as_text=True)

    def test_null_columns_serialise_as_empty_strings(self, client, mock_session):
        row = {
            "session_id": 1,
            "device_name": None,
            "city": None,
            "ip_address": None,
            "created_at": NOW,
            "token_hash": "hash1",
        }
        with patch("api.sessions.get_cache", return_value=None), \
             patch("api.sessions.fetch_all", return_value=[row]), \
             patch("api.sessions.set_cache"):
            resp = client.get(self.URL, headers=SESSION_H)
        assert resp.status_code == 200
        item = resp.get_json()["data"][0]
        assert (item["device_name"], item["city"], item["ip_address"]) == ("", "", "")

    def test_no_auth_returns_401(self, client):
        resp = client.get(self.URL)
        assert resp.status_code == 401

    def test_null_created_at_handled(self, client, mock_session):
        row = {
            "session_id": 2,
            "device_name": "Safari",
            "city": "Toshkent",
            "ip_address": "127.0.0.1",
            "created_at": None,
            "token_hash": "hash2",
        }
        with patch("api.sessions.fetch_one", return_value={"device_name": "Safari"}), \
             patch("api.sessions.get_cache", return_value=None), \
             patch("api.sessions.fetch_all", return_value=[row]), \
             patch("api.sessions.set_cache"):
            resp = client.get(self.URL, headers=SESSION_H)
        item = resp.get_json()["data"][0]
        assert item["created_at"] is None


# ─── DELETE /api/sessions/<session_id> ───────────────────────────────────────

class TestDeleteSession:
    def test_success(self, client, mock_session):
        sess_row = {
            "session_id": 5,
            "token_hash": "oldhash",
        }
        with patch("api.sessions.fetch_one", return_value=sess_row), \
             patch("api.sessions.execute"), \
             patch("api.sessions.invalidate_session_cache"), \
             patch("api.sessions.invalidate_cache"):
            resp = client.delete("/api/sessions/5", headers=SESSION_H)
        assert resp.status_code == 200
        assert resp.get_json()["data"]["deleted"] is True

    def test_session_not_found_returns_404(self, client, mock_session):
        with patch("api.sessions.fetch_one", return_value=None):
            resp = client.delete("/api/sessions/999", headers=SESSION_H)
        assert resp.status_code == 404

    def test_session_cache_invalidated(self, client, mock_session):
        sess_row = {"session_id": 5, "token_hash": "oldhash"}
        with patch("api.sessions.fetch_one", return_value=sess_row), \
             patch("api.sessions.execute"), \
             patch("api.sessions.invalidate_session_cache") as mock_inv, \
             patch("api.sessions.invalidate_cache"):
            resp = client.delete("/api/sessions/5", headers=SESSION_H)
        assert resp.status_code == 200
        mock_inv.assert_called_once_with("oldhash")

    def test_settings_cache_also_invalidated(self, client, mock_session):
        sess_row = {"session_id": 5, "token_hash": "oldhash"}
        with patch("api.sessions.fetch_one", return_value=sess_row), \
             patch("api.sessions.execute"), \
             patch("api.sessions.invalidate_session_cache"), \
             patch("api.sessions.invalidate_cache") as mock_inv:
            resp = client.delete("/api/sessions/5", headers=SESSION_H)
        assert mock_inv.call_count == 2  # sessions cache + settings cache

    def test_no_auth_returns_401(self, client):
        resp = client.delete("/api/sessions/5")
        assert resp.status_code == 401

    def test_cannot_delete_other_user_session(self, client, mock_session):
        """u_id tekshiruvi — boshqa foydalanuvchi sessiyasi o'chirilmasligi kerak."""
        with patch("api.sessions.fetch_one", return_value=None):  # u_id filter bilan topilmaydi
            resp = client.delete("/api/sessions/999", headers=SESSION_H)
        assert resp.status_code == 404


# ─── POST /api/logout ─────────────────────────────────────────────────────────

class TestLogout:
    URL = "/api/logout"

    def test_deletes_the_current_session_and_its_caches(self, client, mock_session):
        from conftest import get_test_token_hash
        with patch("middleware.require_session.execute") as mock_exec, \
             patch("middleware.require_session.invalidate_cache") as mock_inv:
            resp = client.post(self.URL, headers=SESSION_H)
        assert resp.status_code == 200
        assert resp.get_json()["data"] == {"logged_out": True}
        sql, params = mock_exec.call_args[0]
        assert "DELETE FROM sessions" in sql
        assert params == (get_test_token_hash(),)
        dropped = {c[0][0] for c in mock_inv.call_args_list}
        assert f"session_{get_test_token_hash()}" in dropped
        assert f"sessions_{TEST_U_ID}" in dropped

    def test_requires_a_session(self, client):
        resp = client.post(self.URL, headers=WEB_HEADERS)
        assert resp.status_code == 401

    def test_without_client_key_is_rejected(self, client):
        resp = client.post(self.URL)
        assert resp.status_code == 401

    def test_db_failure_returns_generic_500(self, client, mock_session):
        with patch("middleware.require_session.execute",
                   side_effect=RuntimeError("dsn=postgres://u:pw@h")):
            resp = client.post(self.URL, headers=SESSION_H)
        assert resp.status_code == 500
        assert "postgres://" not in resp.get_data(as_text=True)
