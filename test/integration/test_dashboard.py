"""
Integration tests — api/dashboard.py
/api/me/dashboard, /api/partners/dashboards, /api/users/<u_id>/dashboard
"""
from unittest.mock import patch, MagicMock

import pytest

from conftest import (
    TEST_API_KEY, TEST_TOKEN, TEST_U_ID,
    FAKE_USER, FAKE_CATEGORY, FAKE_TYPE, FAKE_SEEDLING_ROW, NOW,
)

API_H = {"X-API-KEY": TEST_API_KEY, "Content-Type": "application/json"}
SESSION_H = {"Authorization": f"Bearer {TEST_TOKEN}", "Content-Type": "application/json"}

SALES_SUMMARY = {
    "q1_sold": 10, "q2_sold": 5, "q3_sold": 2, "total_price": 300000,
}

PARTNER_ROW = {
    "u_id": 987654321,
    "u_name": "Hamkor",
    "u_phone": "+998901111111",
    "u_username": "hamkor",
    "u_age": 30,
    "u_photo": None,
    "created_at": NOW,
}


# ─── GET /api/me/dashboard ────────────────────────────────────────────────────

class TestDashboardMe:
    URL = "/api/me/dashboard"

    def _setup_db_mocks(self):
        return {
            "user": FAKE_USER,
            "categories": [FAKE_CATEGORY],
            "types": [FAKE_TYPE],
            "seedlings": [FAKE_SEEDLING_ROW],
            "sales": SALES_SUMMARY,
        }

    def test_success_returns_all_sections(self, client, mock_session):
        m = self._setup_db_mocks()
        with patch("api.dashboard.fetch_one", return_value=m["user"]), \
             patch("api.dashboard.fetch_all", side_effect=[
                 m["categories"], m["types"], m["seedlings"]
             ]), \
             patch("api.dashboard.get_cached_dashboard", return_value=None), \
             patch("api.dashboard.set_cached_dashboard"):
            resp = client.get(self.URL, headers=SESSION_H)
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert "user" in data
        assert "categories" in data
        assert "types" in data
        assert "seedlings" in data

    def test_cached_response_returned(self, client, mock_session):
        cached = {
            "user": FAKE_USER, "categories": [], "types": [], "seedlings": [], "sales_summary": {}
        }
        with patch("api.dashboard.get_cached_dashboard", return_value=cached):
            resp = client.get(self.URL, headers=SESSION_H)
        assert resp.status_code == 200
        assert resp.get_json()["data"]["user"]["u_id"] == TEST_U_ID

    def test_no_auth_returns_401(self, client):
        resp = client.get(self.URL)
        assert resp.status_code == 401

    def test_response_has_sales_summary(self, client, mock_session):
        full_data = {
            "user": FAKE_USER,
            "categories": [FAKE_CATEGORY],
            "types": [FAKE_TYPE],
            "seedlings": [FAKE_SEEDLING_ROW],
            "sales_summary": SALES_SUMMARY,
        }
        with patch("api.dashboard.get_cached_dashboard", return_value=full_data):
            resp = client.get(self.URL, headers=SESSION_H)
        data = resp.get_json()["data"]
        assert data["sales_summary"]["total_price"] == 300000

    def test_result_cached_after_fetch(self, client, mock_session):
        m = self._setup_db_mocks()
        with patch("api.dashboard.fetch_one", return_value=m["user"]), \
             patch("api.dashboard.fetch_all", side_effect=[
                 m["categories"], m["types"], m["seedlings"]
             ]), \
             patch("api.dashboard.get_cached_dashboard", return_value=None), \
             patch("api.dashboard.set_cached_dashboard") as mock_set:
            resp = client.get(self.URL, headers=SESSION_H)
        assert resp.status_code == 200
        mock_set.assert_called_once()


# ─── GET /api/partners/dashboards ────────────────────────────────────────────

class TestPartnerDashboards:
    URL = "/api/partners/dashboards"

    def test_no_partners_returns_empty_list(self, client, mock_session):
        with patch("api.dashboard.fetch_all", return_value=[]), \
             patch("api.dashboard.get_cache", return_value=None), \
             patch("api.dashboard.set_cache"):
            resp = client.get(self.URL, headers=SESSION_H)
        assert resp.status_code == 200
        assert resp.get_json()["data"] == []

    def test_with_partners_returns_structured_data(self, client, mock_session):
        with patch("api.dashboard.get_cache", return_value=None), \
             patch("api.dashboard.fetch_all", side_effect=[
                 [PARTNER_ROW],           # partner list
                 [dict(FAKE_CATEGORY, u_id=987654321, owner_id=987654321)],  # categories
                 [dict(FAKE_TYPE, u_id=987654321, owner_id=987654321)],      # types
                 [dict(FAKE_SEEDLING_ROW, owner_id=987654321)],              # seedlings
             ]), \
             patch("api.dashboard.set_cache"):
            resp = client.get(self.URL, headers=SESSION_H)
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert isinstance(data, list)
        assert len(data) == 1
        assert "partner" in data[0]
        assert "categories" in data[0]
        assert "types" in data[0]
        assert "seedlings" in data[0]

    def test_cached_response(self, client, mock_session):
        cached = [{"partner": PARTNER_ROW, "categories": [], "types": [], "seedlings": []}]
        with patch("api.dashboard.get_cache", return_value=cached):
            resp = client.get(self.URL, headers=SESSION_H)
        assert resp.status_code == 200
        assert len(resp.get_json()["data"]) == 1

    def test_no_auth_returns_401(self, client):
        resp = client.get(self.URL)
        assert resp.status_code == 401


# ─── GET /api/users/<u_id>/dashboard (public) ────────────────────────────────

class TestPublicDashboard:
    def test_success(self, client):
        with patch("api.dashboard.fetch_one", return_value=FAKE_USER), \
             patch("api.dashboard.fetch_all", side_effect=[
                 [FAKE_CATEGORY], [FAKE_TYPE], [FAKE_SEEDLING_ROW]
             ]):
            resp = client.get(f"/api/users/{TEST_U_ID}/dashboard")
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["user"]["u_id"] == TEST_U_ID
        assert "categories" in data
        assert "types" in data
        assert "seedlings" in data

    def test_user_not_found_returns_404(self, client):
        with patch("api.dashboard.fetch_one", return_value=None):
            resp = client.get("/api/users/9999999/dashboard")
        assert resp.status_code == 404
        assert resp.get_json()["error"]["code"] == "NOT_FOUND"

    def test_no_auth_required(self, client):
        """Public endpoint — auth talab qilinmaydi."""
        with patch("api.dashboard.fetch_one", return_value=FAKE_USER), \
             patch("api.dashboard.fetch_all", side_effect=[[], [], []]):
            resp = client.get(f"/api/users/{TEST_U_ID}/dashboard")
        assert resp.status_code == 200

    def test_empty_collections(self, client):
        with patch("api.dashboard.fetch_one", return_value=FAKE_USER), \
             patch("api.dashboard.fetch_all", side_effect=[[], [], []]):
            resp = client.get(f"/api/users/{TEST_U_ID}/dashboard")
        data = resp.get_json()["data"]
        assert data["categories"] == []
        assert data["types"] == []
        assert data["seedlings"] == []

    def test_types_have_image_url_field(self, client):
        type_with_img = dict(FAKE_TYPE)
        type_with_img["i_url"] = "http://img.com/a.jpg"
        with patch("api.dashboard.fetch_one", return_value=FAKE_USER), \
             patch("api.dashboard.fetch_all", side_effect=[
                 [FAKE_CATEGORY], [type_with_img], []
             ]):
            resp = client.get(f"/api/users/{TEST_U_ID}/dashboard")
        t = resp.get_json()["data"]["types"][0]
        assert "i_url" in t
