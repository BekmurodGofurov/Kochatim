"""
Integration tests — api/categories.py
GET/POST/PUT/DELETE barcha endpointlar testlanadi.
"""
from unittest.mock import patch

import pytest

from conftest import TEST_API_KEY, TEST_TOKEN, TEST_U_ID, FAKE_CATEGORY, NOW

API_H = {"X-API-KEY": TEST_API_KEY, "Content-Type": "application/json"}
SESSION_H = {"Authorization": f"Bearer {TEST_TOKEN}", "Content-Type": "application/json"}


# ─── GET /api/categories (session) ───────────────────────────────────────────

class TestListCategoriesMe:
    URL = "/api/categories"

    def test_success_returns_list(self, client, mock_session):
        with patch("api.categories.fetch_all", return_value=[FAKE_CATEGORY]):
            resp = client.get(self.URL, headers=SESSION_H)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True
        assert isinstance(data["data"], list)
        assert data["data"][0]["c_id"] == FAKE_CATEGORY["c_id"]

    def test_empty_list(self, client, mock_session):
        with patch("api.categories.fetch_all", return_value=[]):
            resp = client.get(self.URL, headers=SESSION_H)
        assert resp.get_json()["data"] == []

    def test_no_auth_returns_401(self, client):
        resp = client.get(self.URL)
        assert resp.status_code == 401

    def test_returns_added_at_field(self, client, mock_session):
        with patch("api.categories.fetch_all", return_value=[FAKE_CATEGORY]):
            resp = client.get(self.URL, headers=SESSION_H)
        d = resp.get_json()["data"][0]
        assert "c_id" in d
        assert "c_name" in d


# ─── GET /api/categories/by-user (API key) ───────────────────────────────────

class TestListCategoriesByUser:
    URL = "/api/categories/by-user"

    def test_success(self, client):
        with patch("api.categories.fetch_all", return_value=[FAKE_CATEGORY]):
            resp = client.get(f"{self.URL}?u_id={TEST_U_ID}", headers=API_H)
        assert resp.status_code == 200
        assert resp.get_json()["data"][0]["c_id"] == 1

    def test_missing_u_id_returns_400(self, client):
        resp = client.get(self.URL, headers=API_H)
        assert resp.status_code == 400

    def test_no_api_key_returns_401(self, client):
        resp = client.get(f"{self.URL}?u_id={TEST_U_ID}")
        assert resp.status_code == 401

    def test_no_results(self, client):
        with patch("api.categories.fetch_all", return_value=[]):
            resp = client.get(f"{self.URL}?u_id=9999999", headers=API_H)
        assert resp.get_json()["data"] == []


# ─── POST /api/categories/me (session) ───────────────────────────────────────

class TestCreateCategoryMe:
    URL = "/api/categories/me"

    def test_success_creates_category(self, client, mock_session):
        new_cat = {"c_id": 2, "c_name": "Gulsafsar"}
        with patch("api.categories.fetch_one", return_value=None), \
             patch("api.categories.execute_returning", return_value=new_cat), \
             patch("api.categories.invalidate_dashboard_cache"):
            resp = client.post(self.URL, json={"c_name": "Gulsafsar"}, headers=SESSION_H)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True
        assert data["data"]["created"] is True
        assert data["data"]["c_id"] == 2
        assert data["data"]["c_name"] == "Gulsafsar"

    def test_duplicate_returns_400(self, client, mock_session):
        with patch("api.categories.fetch_one", return_value=FAKE_CATEGORY):
            resp = client.post(self.URL, json={"c_name": "Mevali daraxtlar"}, headers=SESSION_H)
        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "ALREADY_EXISTS"

    def test_missing_c_name_returns_400(self, client, mock_session):
        resp = client.post(self.URL, json={}, headers=SESSION_H)
        assert resp.status_code == 400

    def test_empty_c_name_returns_400(self, client, mock_session):
        resp = client.post(self.URL, json={"c_name": "   "}, headers=SESSION_H)
        assert resp.status_code == 400

    def test_no_auth_returns_401(self, client):
        resp = client.post(self.URL, json={"c_name": "Test"})
        assert resp.status_code == 401


# ─── POST /api/categories (API key) ─────────────────────────────────────────

class TestCreateCategory:
    URL = "/api/categories"

    def test_success_new_category(self, client):
        with patch("api.categories.fetch_one", return_value=None), \
             patch("api.categories.execute"), \
             patch("api.categories.invalidate_dashboard_cache"):
            with patch("api.categories.fetch_one", side_effect=[None, {"c_id": 5}]):
                resp = client.post(self.URL, json={
                    "u_id": TEST_U_ID, "c_name": "Yangi guruh"
                }, headers=API_H)
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert "c_id" in data
        assert "created" in data

    def test_existing_category_returns_created_false(self, client):
        with patch("api.categories.fetch_one", return_value=FAKE_CATEGORY), \
             patch("api.categories.invalidate_dashboard_cache"):
            resp = client.post(self.URL, json={
                "u_id": TEST_U_ID, "c_name": "Mevali daraxtlar"
            }, headers=API_H)
        assert resp.status_code == 200
        assert resp.get_json()["data"]["created"] is False

    def test_missing_u_id_returns_400(self, client):
        resp = client.post(self.URL, json={"c_name": "X"}, headers=API_H)
        assert resp.status_code == 400

    def test_missing_c_name_returns_400(self, client):
        resp = client.post(self.URL, json={"u_id": TEST_U_ID}, headers=API_H)
        assert resp.status_code == 400

    def test_no_api_key_returns_401(self, client):
        resp = client.post(self.URL, json={"u_id": TEST_U_ID, "c_name": "X"})
        assert resp.status_code == 401


# ─── PUT /api/categories/<c_id> ──────────────────────────────────────────────

class TestUpdateCategory:
    def test_success(self, client):
        with patch("api.categories.execute"), \
             patch("api.categories.invalidate_dashboard_cache"):
            resp = client.put(
                "/api/categories/1",
                json={"u_id": TEST_U_ID, "c_name": "Yangilangan"},
                headers=API_H,
            )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["data"]["updated"] is True
        assert data["data"]["c_id"] == 1

    def test_missing_u_id_returns_400(self, client):
        resp = client.put("/api/categories/1", json={"c_name": "X"}, headers=API_H)
        assert resp.status_code == 400

    def test_missing_c_name_returns_400(self, client):
        resp = client.put("/api/categories/1", json={"u_id": TEST_U_ID}, headers=API_H)
        assert resp.status_code == 400

    def test_no_api_key_returns_401(self, client):
        resp = client.put("/api/categories/1", json={"u_id": TEST_U_ID, "c_name": "X"})
        assert resp.status_code == 401

    def test_empty_c_name_returns_400(self, client):
        resp = client.put(
            "/api/categories/1",
            json={"u_id": TEST_U_ID, "c_name": ""},
            headers=API_H,
        )
        assert resp.status_code == 400


# ─── DELETE /api/categories/<c_id> ───────────────────────────────────────────

class TestDeleteCategory:
    def test_success(self, client):
        with patch("api.categories.execute"), \
             patch("api.categories.invalidate_dashboard_cache"):
            resp = client.delete(
                f"/api/categories/1?u_id={TEST_U_ID}",
                headers=API_H,
            )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["data"]["deleted"] is True
        assert data["data"]["c_id"] == 1

    def test_missing_u_id_returns_400(self, client):
        resp = client.delete("/api/categories/1", headers=API_H)
        assert resp.status_code == 400

    def test_no_api_key_returns_401(self, client):
        resp = client.delete(f"/api/categories/1?u_id={TEST_U_ID}")
        assert resp.status_code == 401
