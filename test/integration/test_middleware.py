"""
Integration tests — middleware/require_api_key.py va require_session.py
Middleware qatlamlari HTTP so'rovlar orqali testlanadi.
"""
from unittest.mock import patch

import pytest

from conftest import TEST_API_KEY, TEST_TOKEN, TEST_U_ID


# ─── require_api_key ─────────────────────────────────────────────────────────

class TestRequireApiKey:
    def test_missing_api_key_returns_401(self, client):
        resp = client.post(
            "/api/users/ensure",
            json={"u_id": 1},
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 401
        data = resp.get_json()
        assert data["ok"] is False
        assert data["error"]["code"] == "UNAUTHORIZED"

    def test_wrong_api_key_returns_401(self, client):
        resp = client.post(
            "/api/users/ensure",
            json={"u_id": 1},
            headers={"X-API-KEY": "wrong-key", "Content-Type": "application/json"},
        )
        assert resp.status_code == 401

    def test_correct_api_key_passes(self, client, api_key_headers):
        with patch("api.users.execute"), \
             patch("api.users.fetch_one", return_value={"u_id": 99, "u_name": "X",
                                                         "u_phone": None, "u_username": None,
                                                         "u_age": None, "added_at": None,
                                                         "updated_at": None}):
            resp = client.post(
                "/api/users/ensure",
                json={"u_id": 99},
                headers=api_key_headers,
            )
        assert resp.status_code == 200

    def test_api_key_in_x_api_key_header(self, client, api_key_headers):
        with patch("api.users.execute"), \
             patch("api.users.fetch_one", return_value={"u_id": 1}):
            resp = client.get(
                "/api/users/1",
                headers=api_key_headers,
            )
        assert resp.status_code == 200

    def test_empty_api_key_returns_401(self, client):
        resp = client.get(
            "/api/users/1",
            headers={"X-API-KEY": "", "Content-Type": "application/json"},
        )
        assert resp.status_code == 401

    def test_api_key_case_sensitive(self, client):
        upper = {"X-API-KEY": TEST_API_KEY.upper()}
        with patch("api.users.fetch_one", return_value={"u_id": 1}):
            resp = client.get("/api/users/1", headers=upper)
        if TEST_API_KEY.upper() != TEST_API_KEY:
            assert resp.status_code == 401


# ─── require_session ─────────────────────────────────────────────────────────

class TestRequireSession:
    def test_missing_authorization_returns_401(self, client):
        resp = client.get("/api/me")
        assert resp.status_code == 401
        data = resp.get_json()
        assert data["ok"] is False
        assert data["error"]["code"] == "UNAUTHORIZED"

    def test_wrong_prefix_returns_401(self, client):
        resp = client.get(
            "/api/me",
            headers={"Authorization": "Basic sometoken"},
        )
        assert resp.status_code == 401

    def test_empty_token_returns_401(self, client):
        resp = client.get(
            "/api/me",
            headers={"Authorization": "Bearer "},
        )
        assert resp.status_code == 401

    def test_invalid_token_returns_401(self, client):
        with patch("middleware.require_session.get_cache", return_value=None), \
             patch("middleware.require_session.fetch_one", return_value=None):
            resp = client.get(
                "/api/me",
                headers={"Authorization": "Bearer invalid-token-xyz"},
            )
        assert resp.status_code == 401

    def test_valid_token_from_cache_passes(self, client, mock_session, session_headers):
        with patch("api.users.fetch_one", return_value={
            "u_id": TEST_U_ID, "u_name": "Test", "u_phone": None,
            "u_username": None, "u_age": None, "added_at": None, "updated_at": None,
        }):
            resp = client.get("/api/me", headers=session_headers)
        assert resp.status_code == 200

    def test_valid_token_from_db_passes(self, client, mock_session_miss, session_headers):
        with patch("api.users.fetch_one", return_value={
            "u_id": TEST_U_ID, "u_name": "Test", "u_phone": None,
            "u_username": None, "u_age": None, "added_at": None, "updated_at": None,
        }):
            resp = client.get("/api/me", headers=session_headers)
        assert resp.status_code == 200

    def test_expired_session_returns_401(self, client):
        with patch("middleware.require_session.get_cache", return_value=None), \
             patch("middleware.require_session.fetch_one", return_value=None):
            resp = client.get(
                "/api/me",
                headers={"Authorization": f"Bearer {TEST_TOKEN}"},
            )
        assert resp.status_code == 401

    def test_g_uid_set_correctly(self, client, mock_session, session_headers):
        """g.u_id to'g'ri o'rnatilganini endpoint orqali tekshirish."""
        with patch("api.users.fetch_one", return_value={
            "u_id": TEST_U_ID, "u_name": "Test", "u_phone": None,
            "u_username": None, "u_age": None, "added_at": None, "updated_at": None,
        }) as mock:
            resp = client.get("/api/me", headers=session_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["data"]["u_id"] == TEST_U_ID


# ─── Health endpoint (middleware yo'q) ───────────────────────────────────────

class TestHealthEndpoint:
    def test_health_check(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True
        assert data["data"]["status"] == "up"

    def test_404_returns_json(self, client):
        resp = client.get("/nonexistent-path-xyz")
        assert resp.status_code == 404
        data = resp.get_json()
        assert data["ok"] is False
