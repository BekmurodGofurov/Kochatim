"""
Integration tests — api/types.py
Ko'chat turlari (types) CRUD endpointlar.
"""
from unittest.mock import patch

import pytest

from conftest import TEST_API_KEY, TEST_TOKEN, TEST_U_ID, FAKE_TYPE, FAKE_CATEGORY, NOW
from conftest import SESSION_HEADERS, WEB_HEADERS

API_H = {"X-API-KEY": TEST_API_KEY, "Content-Type": "application/json"}
SESSION_H = dict(SESSION_HEADERS)


# ─── POST /api/types/me (session) ────────────────────────────────────────────

class TestCreateTypeMe:
    URL = "/api/types/me"

    def test_success(self, client, mock_session):
        with patch("api.types.fetch_one", side_effect=[FAKE_CATEGORY, None]), \
             patch("api.types.execute_returning", return_value=FAKE_TYPE), \
             patch("api.types.execute"), \
             patch("api.types.invalidate_dashboard_cache"):
            resp = client.post(self.URL, json={
                "c_id": 1,
                "t_name": "Olma",
                "deff": "Yaxshi nav",
            }, headers=SESSION_H)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True
        assert data["data"]["t_id"] == FAKE_TYPE["t_id"]
        assert data["data"]["t_name"] == "Olma"

    def test_missing_c_id_returns_400(self, client, mock_session):
        resp = client.post(self.URL, json={"t_name": "Olma"}, headers=SESSION_H)
        assert resp.status_code == 400

    def test_missing_t_name_returns_400(self, client, mock_session):
        resp = client.post(self.URL, json={"c_id": 1}, headers=SESSION_H)
        assert resp.status_code == 400

    def test_category_not_found_returns_404(self, client, mock_session):
        with patch("api.types.fetch_one", return_value=None):
            resp = client.post(self.URL, json={"c_id": 999, "t_name": "X"}, headers=SESSION_H)
        assert resp.status_code == 404
        assert resp.get_json()["error"]["code"] == "NOT_FOUND"

    def test_no_auth_returns_401(self, client):
        resp = client.post(self.URL, json={"c_id": 1, "t_name": "X"})
        assert resp.status_code == 401

    def test_c_id_as_dict_object_parsed(self, client, mock_session):
        """Bot ba'zida c_id ni object sifatida yuboradi — _to_int() ni tekshirish."""
        with patch("api.types.fetch_one", side_effect=[FAKE_CATEGORY, None]), \
             patch("api.types.execute_returning", return_value=FAKE_TYPE), \
             patch("api.types.execute"), \
             patch("api.types.invalidate_dashboard_cache"):
            resp = client.post(self.URL, json={
                "c_id": {"c_id": 1, "c_name": "Mevali"},
                "t_name": "Olma",
            }, headers=SESSION_H)
        assert resp.status_code == 200

    def test_with_image_url(self, client, mock_session):
        with patch("api.types.fetch_one", side_effect=[FAKE_CATEGORY, None]), \
             patch("api.types.execute_returning", return_value=FAKE_TYPE), \
             patch("api.types.execute"), \
             patch("api.types.process_image_input", return_value="http://img.com/a.jpg"), \
             patch("api.types.invalidate_dashboard_cache"):
            resp = client.post(self.URL, json={
                "c_id": 1, "t_name": "Olma", "image_url": "AgACAg123",
            }, headers=SESSION_H)
        assert resp.status_code == 200

    def test_empty_t_name_returns_400(self, client, mock_session):
        resp = client.post(self.URL, json={"c_id": 1, "t_name": ""}, headers=SESSION_H)
        assert resp.status_code == 400


# ─── POST /api/types (API key) ───────────────────────────────────────────────


class TestCreateType:
    URL = "/api/types"
    BODY = {"u_id": TEST_U_ID, "c_id": 1, "t_name": "Nok"}

    def _post(self, client, body=None, owns_category=True):
        with patch("api.types.fetch_one", return_value={"c_id": 1} if owns_category else None) as own, \
             patch("api.types.execute_returning", return_value=FAKE_TYPE) as ins, \
             patch("api.types.invalidate_dashboard_cache") as inv:
            resp = client.post(self.URL, json=self.BODY if body is None else body, headers=API_H)
        return resp, own, ins, inv

    def test_success(self, client):
        resp, _, _, inv = self._post(client)
        assert resp.status_code == 200
        assert resp.get_json()["data"]["t_id"] is not None
        inv.assert_called_once_with(TEST_U_ID)

    def test_the_category_must_belong_to_the_user(self, client):
        """Attaching a variety to someone else's group must fail."""
        resp, own, ins, inv = self._post(client, owns_category=False)
        assert resp.status_code == 404
        assert resp.get_json()["error"]["code"] == "NOT_FOUND"
        ins.assert_not_called()
        inv.assert_not_called()

    def test_ownership_is_checked_with_both_ids_as_parameters(self, client):
        _, own, *_ = self._post(client)
        sql, params = own.call_args[0]
        assert "categories" in sql and "u_id" in sql and "c_id" in sql
        assert params == (1, TEST_U_ID)

    def test_missing_u_id_returns_400(self, client):
        resp, _, ins, _ = self._post(client, {"c_id": 1, "t_name": "X"})
        assert resp.status_code == 400
        ins.assert_not_called()

    def test_missing_c_id_returns_400(self, client):
        assert self._post(client, {"u_id": TEST_U_ID, "t_name": "X"})[0].status_code == 400

    def test_missing_t_name_returns_400(self, client):
        assert self._post(client, {"u_id": TEST_U_ID, "c_id": 1})[0].status_code == 400

    def test_no_api_key_returns_401(self, client):
        assert client.post(self.URL, json=self.BODY).status_code == 401

    def test_web_client_key_is_not_enough(self, client):
        assert client.post(self.URL, json=self.BODY, headers=WEB_HEADERS).status_code == 401

    def test_database_failure_returns_generic_500(self, client):
        with patch("api.types.fetch_one", side_effect=RuntimeError("dsn=postgres://u:hunter2@db")):
            resp = client.post(self.URL, json=self.BODY, headers=API_H)
        assert resp.status_code == 500
        assert "hunter2" not in resp.get_data(as_text=True)


# ─── GET /api/types (API key) ────────────────────────────────────────────────

class TestListTypes:
    URL = "/api/types"

    def test_success_all(self, client):
        with patch("api.types.fetch_all", return_value=[FAKE_TYPE]):
            resp = client.get(self.URL, headers=API_H)
        assert resp.status_code == 200
        assert isinstance(resp.get_json()["data"], list)

    def test_filter_by_u_id(self, client):
        with patch("api.types.fetch_all", return_value=[FAKE_TYPE]):
            resp = client.get(f"{self.URL}?u_id={TEST_U_ID}", headers=API_H)
        assert resp.status_code == 200

    def test_filter_by_c_id(self, client):
        with patch("api.types.fetch_all", return_value=[FAKE_TYPE]):
            resp = client.get(f"{self.URL}?c_id=1", headers=API_H)
        assert resp.status_code == 200

    def test_no_api_key_returns_401(self, client):
        resp = client.get(self.URL)
        assert resp.status_code == 401


# ─── GET /api/types/by-user (API key) ────────────────────────────────────────

class TestListTypesByUser:
    URL = "/api/types/by-user"

    def test_success(self, client):
        with patch("api.types.fetch_all", return_value=[FAKE_TYPE]):
            resp = client.get(f"{self.URL}?u_id={TEST_U_ID}&c_id=1", headers=API_H)
        assert resp.status_code == 200

    def test_missing_u_id_returns_400(self, client):
        resp = client.get(f"{self.URL}?c_id=1", headers=API_H)
        assert resp.status_code == 400

    def test_missing_c_id_returns_400(self, client):
        resp = client.get(f"{self.URL}?u_id={TEST_U_ID}", headers=API_H)
        assert resp.status_code == 400


# ─── GET /api/types/<t_id> (API key) ─────────────────────────────────────────

class TestGetType:
    def test_success(self, client):
        with patch("api.types.fetch_one", return_value=FAKE_TYPE):
            resp = client.get("/api/types/10", headers=API_H)
        assert resp.status_code == 200
        assert resp.get_json()["data"]["t_id"] == 10

    def test_not_found_returns_404(self, client):
        with patch("api.types.fetch_one", return_value=None):
            resp = client.get("/api/types/9999", headers=API_H)
        assert resp.status_code == 404
        assert resp.get_json()["error"]["code"] == "NOT_FOUND"

    def test_no_api_key_returns_401(self, client):
        resp = client.get("/api/types/10")
        assert resp.status_code == 401


# ─── GET /api/type-info (API key) ────────────────────────────────────────────

class TestTypeInfo:
    URL = "/api/type-info"

    def test_success(self, client):
        info = {"t_id": 10, "t_name": "Olma", "deff": "Yaxshi"}
        with patch("api.types.fetch_one", return_value=info):
            resp = client.get(f"{self.URL}?u_id={TEST_U_ID}&t_id=10", headers=API_H)
        assert resp.status_code == 200
        assert resp.get_json()["data"]["t_name"] == "Olma"

    def test_missing_u_id_returns_400(self, client):
        resp = client.get(f"{self.URL}?t_id=10", headers=API_H)
        assert resp.status_code == 400

    def test_missing_t_id_returns_400(self, client):
        resp = client.get(f"{self.URL}?u_id={TEST_U_ID}", headers=API_H)
        assert resp.status_code == 400

    def test_not_found_returns_404(self, client):
        with patch("api.types.fetch_one", return_value=None):
            resp = client.get(f"{self.URL}?u_id={TEST_U_ID}&t_id=9999", headers=API_H)
        assert resp.status_code == 404


# ─── PUT /api/types/<t_id> (API key) ─────────────────────────────────────────

class TestUpdateType:
    def test_success(self, client):
        with patch("api.types.execute"), \
             patch("api.types.invalidate_dashboard_cache"):
            resp = client.put("/api/types/10", json={
                "u_id": TEST_U_ID, "t_name": "Yangi olma",
            }, headers=API_H)
        assert resp.status_code == 200
        assert resp.get_json()["data"]["updated"] is True

    def test_missing_u_id_returns_400(self, client):
        resp = client.put("/api/types/10", json={"t_name": "X"}, headers=API_H)
        assert resp.status_code == 400

    def test_missing_t_name_returns_400(self, client):
        resp = client.put("/api/types/10", json={"u_id": TEST_U_ID}, headers=API_H)
        assert resp.status_code == 400


# ─── DELETE /api/types/<t_id> (API key) ──────────────────────────────────────

class TestDeleteType:
    def test_success(self, client):
        with patch("api.types.execute"), \
             patch("api.types.invalidate_dashboard_cache"):
            resp = client.delete(f"/api/types/10?u_id={TEST_U_ID}", headers=API_H)
        assert resp.status_code == 200
        assert resp.get_json()["data"]["deleted"] is True
        assert resp.get_json()["data"]["t_id"] == 10

    def test_missing_u_id_returns_400(self, client):
        resp = client.delete("/api/types/10", headers=API_H)
        assert resp.status_code == 400

    def test_no_api_key_returns_401(self, client):
        resp = client.delete(f"/api/types/10?u_id={TEST_U_ID}")
        assert resp.status_code == 401
