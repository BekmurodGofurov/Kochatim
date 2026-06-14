"""
Integration tests — api/seedlings.py
Ko'chat zahirasi endpointlari: count, set, get, update
"""
from unittest.mock import patch

import pytest

from conftest import TEST_API_KEY, TEST_TOKEN, TEST_U_ID, FAKE_SEEDLING_ROW, NOW

API_H = {"X-API-KEY": TEST_API_KEY, "Content-Type": "application/json"}
SESSION_H = {"Authorization": f"Bearer {TEST_TOKEN}", "Content-Type": "application/json"}

STOCK_ROW = {"quality_1": 100, "quality_2": 50, "quality_3": 25}


# ─── GET /api/seedlings/count (API key) ───────────────────────────────────────

class TestSeedlingsCount:
    URL = "/api/seedlings/count"

    def test_success_existing_record(self, client):
        with patch("api.seedlings.fetch_one", return_value=STOCK_ROW):
            resp = client.get(f"{self.URL}?u_id={TEST_U_ID}&t_id=10", headers=API_H)
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["quality_1"] == 100
        assert data["quality_2"] == 50
        assert data["quality_3"] == 25
        assert data["t_id"] == 10

    def test_no_record_returns_zeros(self, client):
        with patch("api.seedlings.fetch_one", return_value=None):
            resp = client.get(f"{self.URL}?u_id={TEST_U_ID}&t_id=999", headers=API_H)
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["quality_1"] == 0
        assert data["quality_2"] == 0
        assert data["quality_3"] == 0

    def test_missing_u_id_returns_400(self, client):
        resp = client.get(f"{self.URL}?t_id=10", headers=API_H)
        assert resp.status_code == 400

    def test_missing_t_id_returns_400(self, client):
        resp = client.get(f"{self.URL}?u_id={TEST_U_ID}", headers=API_H)
        assert resp.status_code == 400

    def test_no_api_key_returns_401(self, client):
        resp = client.get(f"{self.URL}?u_id={TEST_U_ID}&t_id=10")
        assert resp.status_code == 401

    def test_null_values_treated_as_zero(self, client):
        with patch("api.seedlings.fetch_one", return_value={"quality_1": None, "quality_2": None, "quality_3": None}):
            resp = client.get(f"{self.URL}?u_id={TEST_U_ID}&t_id=10", headers=API_H)
        data = resp.get_json()["data"]
        assert data["quality_1"] == 0
        assert data["quality_2"] == 0
        assert data["quality_3"] == 0


# ─── POST /api/seedlings/set (API key) ────────────────────────────────────────

class TestSeedlingsSet:
    URL = "/api/seedlings/set"

    def test_insert_new_record(self, client):
        with patch("api.seedlings.fetch_one", return_value=None), \
             patch("api.seedlings.execute"), \
             patch("api.seedlings.invalidate_dashboard_cache"):
            resp = client.post(self.URL, json={
                "u_id": TEST_U_ID, "t_id": 10,
                "quality_1": 50, "quality_2": 30, "quality_3": 10,
            }, headers=API_H)
        assert resp.status_code == 200
        assert resp.get_json()["data"]["saved"] is True

    def test_update_existing_record(self, client):
        existing = {"s_id": 1}
        with patch("api.seedlings.fetch_one", return_value=existing), \
             patch("api.seedlings.execute"), \
             patch("api.seedlings.invalidate_dashboard_cache"):
            resp = client.post(self.URL, json={
                "u_id": TEST_U_ID, "t_id": 10,
                "quality_1": 10, "quality_2": 5, "quality_3": 2,
            }, headers=API_H)
        assert resp.status_code == 200
        assert resp.get_json()["data"]["saved"] is True

    def test_missing_u_id_returns_400(self, client):
        resp = client.post(self.URL, json={"t_id": 10}, headers=API_H)
        assert resp.status_code == 400

    def test_missing_t_id_returns_400(self, client):
        resp = client.post(self.URL, json={"u_id": TEST_U_ID}, headers=API_H)
        assert resp.status_code == 400

    def test_string_u_id_returns_400(self, client):
        resp = client.post(self.URL, json={"u_id": "abc", "t_id": 10}, headers=API_H)
        assert resp.status_code == 400

    def test_no_api_key_returns_401(self, client):
        resp = client.post(self.URL, json={"u_id": TEST_U_ID, "t_id": 10})
        assert resp.status_code == 401

    def test_default_zero_quantities(self, client):
        with patch("api.seedlings.fetch_one", return_value=None), \
             patch("api.seedlings.execute"), \
             patch("api.seedlings.invalidate_dashboard_cache"):
            resp = client.post(self.URL, json={"u_id": TEST_U_ID, "t_id": 10}, headers=API_H)
        assert resp.status_code == 200


# ─── GET /api/seedlings (session) ─────────────────────────────────────────────

class TestSeedlingsGetMe:
    URL = "/api/seedlings"

    def test_success_with_stock(self, client, mock_session):
        with patch("api.seedlings.fetch_one", return_value=STOCK_ROW):
            resp = client.get(f"{self.URL}?t_id=10", headers=SESSION_H)
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["quality_1"] == 100
        assert data["t_id"] == 10

    def test_no_stock_returns_zeros(self, client, mock_session):
        with patch("api.seedlings.fetch_one", return_value=None):
            resp = client.get(f"{self.URL}?t_id=10", headers=SESSION_H)
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["quality_1"] == 0

    def test_missing_t_id_returns_400(self, client, mock_session):
        resp = client.get(self.URL, headers=SESSION_H)
        assert resp.status_code == 400

    def test_no_auth_returns_401(self, client):
        resp = client.get(f"{self.URL}?t_id=10")
        assert resp.status_code == 401


# ─── POST /api/seedlings/update (session) ─────────────────────────────────────

class TestSeedlingsUpdateMe:
    URL = "/api/seedlings/update"

    def test_success_add_stock(self, client, mock_session):
        existing = {"s_id": 1, "quality_1": 100, "quality_2": 50, "quality_3": 25}
        with patch("api.seedlings.fetch_one", return_value=existing), \
             patch("api.seedlings.execute"), \
             patch("api.seedlings.invalidate_dashboard_cache"):
            resp = client.post(self.URL, json={
                "t_id": 10, "change_q1": 10, "change_q2": 5, "change_q3": 0,
            }, headers=SESSION_H)
        assert resp.status_code == 200
        assert resp.get_json()["data"]["saved"] is True

    def test_success_deduct_stock(self, client, mock_session):
        existing = {"s_id": 1, "quality_1": 100, "quality_2": 50, "quality_3": 25}
        with patch("api.seedlings.fetch_one", return_value=existing), \
             patch("api.seedlings.execute"), \
             patch("api.seedlings.invalidate_dashboard_cache"):
            resp = client.post(self.URL, json={
                "t_id": 10, "change_q1": -10, "change_q2": -5, "change_q3": 0,
            }, headers=SESSION_H)
        assert resp.status_code == 200

    def test_insufficient_stock_returns_400(self, client, mock_session):
        existing = {"s_id": 1, "quality_1": 5, "quality_2": 3, "quality_3": 1}
        with patch("api.seedlings.fetch_one", return_value=existing):
            resp = client.post(self.URL, json={
                "t_id": 10, "change_q1": -100, "change_q2": 0, "change_q3": 0,
            }, headers=SESSION_H)
        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "INSUFFICIENT_STOCK"

    def test_negative_insert_returns_400(self, client, mock_session):
        with patch("api.seedlings.fetch_one", return_value=None):
            resp = client.post(self.URL, json={
                "t_id": 10, "change_q1": -5, "change_q2": 0, "change_q3": 0,
            }, headers=SESSION_H)
        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "INSUFFICIENT_STOCK"

    def test_missing_t_id_returns_400(self, client, mock_session):
        resp = client.post(self.URL, json={"change_q1": 10}, headers=SESSION_H)
        assert resp.status_code == 400

    def test_string_t_id_returns_400(self, client, mock_session):
        resp = client.post(self.URL, json={"t_id": "abc"}, headers=SESSION_H)
        assert resp.status_code == 400

    def test_no_auth_returns_401(self, client):
        resp = client.post(self.URL, json={"t_id": 10})
        assert resp.status_code == 401

    def test_zero_changes_accepted(self, client, mock_session):
        existing = {"s_id": 1, "quality_1": 10, "quality_2": 5, "quality_3": 2}
        with patch("api.seedlings.fetch_one", return_value=existing), \
             patch("api.seedlings.execute"), \
             patch("api.seedlings.invalidate_dashboard_cache"):
            resp = client.post(self.URL, json={
                "t_id": 10, "change_q1": 0, "change_q2": 0, "change_q3": 0,
            }, headers=SESSION_H)
        assert resp.status_code == 200

    def test_log_entry_created(self, client, mock_session):
        """seedlings_logs ga yozilishini execute chaqiruvlari orqali tekshirish."""
        existing = {"s_id": 1, "quality_1": 50, "quality_2": 20, "quality_3": 10}
        with patch("api.seedlings.fetch_one", return_value=existing), \
             patch("api.seedlings.execute") as mock_exec, \
             patch("api.seedlings.invalidate_dashboard_cache"):
            resp = client.post(self.URL, json={
                "t_id": 10, "change_q1": 5, "change_q2": 0, "change_q3": 0,
                "comment": "Test log",
            }, headers=SESSION_H)
        assert resp.status_code == 200
        # Ikki marta execute chaqirilishi kerak: UPDATE + INSERT log
        assert mock_exec.call_count == 2
