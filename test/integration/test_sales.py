"""
Integration tests — api/sales.py
Sotuv qo'shish va sotuv tarixi endpointlari.
"""
from datetime import datetime
from unittest.mock import patch

import pytest

from conftest import TEST_API_KEY, TEST_TOKEN, TEST_U_ID, NOW

API_H = {"X-API-KEY": TEST_API_KEY, "Content-Type": "application/json"}
SESSION_H = {"Authorization": f"Bearer {TEST_TOKEN}", "Content-Type": "application/json"}

TYPE_ROW = {"t_id": 10}
STOCK_ROW = {"quality_1": 100, "quality_2": 50, "quality_3": 25}
EMPTY_STOCK = {"quality_1": 0, "quality_2": 0, "quality_3": 0}

SALE_HISTORY_ROW = {
    "sale_id": 1, "price": 150000, "sold_at": NOW,
    "q1_sold": 5, "q2_sold": 3, "q3_sold": 1,
    "c_id": 1, "c_name": "Mevali daraxtlar",
    "t_id": 10, "t_name": "Olma",
}


# ─── POST /api/sales (API key) ────────────────────────────────────────────────

class TestAddSale:
    URL = "/api/sales"

    def _valid_body(self, **kwargs):
        data = {
            "u_id": TEST_U_ID, "c_id": 1, "t_id": 10,
            "q1_sold": 5, "q2_sold": 3, "q3_sold": 1, "price": 150000,
        }
        data.update(kwargs)
        return data

    def test_success(self, client):
        with patch("api.sales.fetch_one", side_effect=[TYPE_ROW, STOCK_ROW]), \
             patch("api.sales.execute"), \
             patch("api.sales.invalidate_dashboard_cache"):
            resp = client.post(self.URL, json=self._valid_body(), headers=API_H)
        assert resp.status_code == 200
        assert resp.get_json()["data"]["saved"] is True

    def test_inventory_deducted_after_sale(self, client):
        """Sotuv qo'shilgandan so'ng execute ikki marta chaqiriladi (INSERT + UPDATE)."""
        with patch("api.sales.fetch_one", side_effect=[TYPE_ROW, STOCK_ROW]), \
             patch("api.sales.execute") as mock_exec, \
             patch("api.sales.invalidate_dashboard_cache"):
            resp = client.post(self.URL, json=self._valid_body(), headers=API_H)
        assert resp.status_code == 200
        assert mock_exec.call_count == 2

    def test_type_not_found_returns_404(self, client):
        with patch("api.sales.fetch_one", side_effect=[None]):
            resp = client.post(self.URL, json=self._valid_body(), headers=API_H)
        assert resp.status_code == 404
        assert resp.get_json()["error"]["code"] == "NOT_FOUND"

    def test_insufficient_stock_returns_400(self, client):
        low_stock = {"quality_1": 1, "quality_2": 0, "quality_3": 0}
        with patch("api.sales.fetch_one", side_effect=[TYPE_ROW, low_stock]):
            resp = client.post(self.URL, json=self._valid_body(q1_sold=100), headers=API_H)
        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "INSUFFICIENT_STOCK"

    def test_missing_u_id_returns_400(self, client):
        body = self._valid_body()
        del body["u_id"]
        resp = client.post(self.URL, json=body, headers=API_H)
        assert resp.status_code == 400

    def test_missing_c_id_returns_400(self, client):
        body = self._valid_body()
        del body["c_id"]
        resp = client.post(self.URL, json=body, headers=API_H)
        assert resp.status_code == 400

    def test_missing_t_id_returns_400(self, client):
        body = self._valid_body()
        del body["t_id"]
        resp = client.post(self.URL, json=body, headers=API_H)
        assert resp.status_code == 400

    def test_invalid_price_returns_400(self, client):
        resp = client.post(self.URL, json=self._valid_body(price="invalid"), headers=API_H)
        assert resp.status_code == 400

    def test_string_u_id_returns_400(self, client):
        resp = client.post(self.URL, json=self._valid_body(u_id="abc"), headers=API_H)
        assert resp.status_code == 400

    def test_no_api_key_returns_401(self, client):
        resp = client.post(self.URL, json=self._valid_body())
        assert resp.status_code == 401

    def test_zero_quantities_accepted(self, client):
        """Nol miqdorli sotuv — stock tekshiruvi o'tkaziladi."""
        with patch("api.sales.fetch_one", side_effect=[TYPE_ROW, STOCK_ROW]), \
             patch("api.sales.execute"), \
             patch("api.sales.invalidate_dashboard_cache"):
            resp = client.post(self.URL, json=self._valid_body(
                q1_sold=0, q2_sold=0, q3_sold=0
            ), headers=API_H)
        assert resp.status_code == 200

    def test_no_stock_record_sale_allowed(self, client):
        """Seedlings jadvali bo'sh bo'lsa sotuv qo'shiladi (stock tekshiruvi faqat mavjudda)."""
        with patch("api.sales.fetch_one", side_effect=[TYPE_ROW, None]), \
             patch("api.sales.execute"), \
             patch("api.sales.invalidate_dashboard_cache"):
            resp = client.post(self.URL, json=self._valid_body(
                q1_sold=0, q2_sold=0, q3_sold=0
            ), headers=API_H)
        assert resp.status_code == 200

    def test_price_zero_accepted(self, client):
        with patch("api.sales.fetch_one", side_effect=[TYPE_ROW, STOCK_ROW]), \
             patch("api.sales.execute"), \
             patch("api.sales.invalidate_dashboard_cache"):
            resp = client.post(self.URL, json=self._valid_body(price=0), headers=API_H)
        assert resp.status_code == 200


# ─── GET /api/sales (session) ─────────────────────────────────────────────────

class TestListSalesMe:
    URL = "/api/sales"

    def test_success_returns_history_and_pie(self, client, mock_session):
        pie_row = {"name": "Mevali daraxtlar", "value": 150000}
        with patch("api.sales.fetch_all", side_effect=[[SALE_HISTORY_ROW], [pie_row]]):
            resp = client.get(self.URL, headers=SESSION_H)
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert "history" in data
        assert "pie" in data

    def test_history_has_ui_fields(self, client, mock_session):
        with patch("api.sales.fetch_all", side_effect=[[SALE_HISTORY_ROW], []]):
            resp = client.get(self.URL, headers=SESSION_H)
        item = resp.get_json()["data"]["history"][0]
        assert "id" in item
        assert "name" in item
        assert "category" in item
        assert "date" in item
        assert "qty" in item
        assert "price" in item

    def test_qty_is_sum_of_all_qualities(self, client, mock_session):
        with patch("api.sales.fetch_all", side_effect=[[SALE_HISTORY_ROW], []]):
            resp = client.get(self.URL, headers=SESSION_H)
        item = resp.get_json()["data"]["history"][0]
        expected_qty = 5 + 3 + 1
        assert item["qty"] == expected_qty

    def test_empty_sales_returns_empty_lists(self, client, mock_session):
        with patch("api.sales.fetch_all", side_effect=[[], []]):
            resp = client.get(self.URL, headers=SESSION_H)
        data = resp.get_json()["data"]
        assert data["history"] == []
        assert data["pie"] == []

    def test_no_auth_returns_401(self, client):
        resp = client.get(self.URL)
        assert resp.status_code == 401

    def test_pie_has_name_and_value(self, client, mock_session):
        pie = [{"name": "Guruh A", "value": 500000}]
        with patch("api.sales.fetch_all", side_effect=[[], pie]):
            resp = client.get(self.URL, headers=SESSION_H)
        pie_data = resp.get_json()["data"]["pie"]
        assert len(pie_data) == 1
        assert pie_data[0]["name"] == "Guruh A"

    def test_null_c_name_handled(self, client, mock_session):
        row_null = dict(SALE_HISTORY_ROW)
        row_null["c_name"] = None
        row_null["t_name"] = None
        with patch("api.sales.fetch_all", side_effect=[[row_null], []]):
            resp = client.get(self.URL, headers=SESSION_H)
        item = resp.get_json()["data"]["history"][0]
        assert item["name"] == "—"
        assert item["category"] == "—"
