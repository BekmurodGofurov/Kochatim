"""
Integration tests — api/sales.py
Sotuv qo'shish va sotuv tarixi endpointlari.
"""
from datetime import datetime
from unittest.mock import patch

import pytest

from conftest import TEST_API_KEY, TEST_TOKEN, TEST_U_ID, NOW
from conftest import SESSION_HEADERS, WEB_HEADERS

API_H = {"X-API-KEY": TEST_API_KEY, "Content-Type": "application/json"}
SESSION_H = dict(SESSION_HEADERS)

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


class _FakeTx:
    """Stands in for db.transaction(): records statements, can report rowcount, can fail."""

    def __init__(self, updated=1, stock=None, fail_on_insert=False):
        self.statements = []
        self.updated = updated
        self.stock = stock
        self.fail_on_insert = fail_on_insert
        self.committed = False
        self.rolled_back = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            self.committed = True
        else:
            self.rolled_back = True
        return False  # never swallow: the handler / error handlers decide the response

    def execute(self, sql, params=()):
        self.statements.append((sql, params))
        if "INSERT INTO sales" in sql and self.fail_on_insert:
            raise RuntimeError("connection dropped")
        return self.updated if "UPDATE seedlings" in sql else 1

    def fetch_one(self, sql, params=()):
        self.statements.append((sql, params))
        return self.stock


class TestAddSale:
    URL = "/api/sales"

    def _valid_body(self, **kwargs):
        data = {
            "u_id": TEST_U_ID, "c_id": 1, "t_id": 10,
            "q1_sold": 5, "q2_sold": 3, "q3_sold": 1, "price": 150000,
        }
        data.update(kwargs)
        return data

    def _post(self, client, body=None, tx=None, owner=TYPE_ROW):
        tx = tx or _FakeTx()
        with patch("api.sales.fetch_one", return_value=owner), \
             patch("api.sales.transaction", return_value=tx), \
             patch("api.sales.invalidate_dashboard_cache") as inv:
            resp = client.post(self.URL, json=self._valid_body() if body is None else body, headers=API_H)
        return resp, tx, inv

    def test_success(self, client):
        resp, tx, inv = self._post(client)
        assert resp.status_code == 200
        assert resp.get_json()["data"]["saved"] is True
        inv.assert_called_once_with(TEST_U_ID)

    def test_stock_and_sale_are_written_in_one_transaction(self, client):
        resp, tx, _ = self._post(client)
        sqls = [s for s, _ in tx.statements]
        assert tx.committed and not tx.rolled_back
        assert "UPDATE seedlings" in sqls[0] and "INSERT INTO sales" in sqls[-1]

    def test_stock_is_deducted_by_a_guarded_statement(self, client):
        _, tx, _ = self._post(client)
        sql, params = tx.statements[0]
        assert "quality_1 - %s >= 0" in sql.replace("COALESCE(quality_1, 0)", "quality_1")
        assert params[:5] == (5, 3, 1, TEST_U_ID, 10)

    def test_a_failure_after_the_stock_update_rolls_everything_back(self, client):
        """The old two-commit code could take the stock and lose the sale, or the reverse."""
        tx = _FakeTx(fail_on_insert=True)
        resp, tx, inv = self._post(client, tx=tx)
        assert resp.status_code == 500
        assert tx.rolled_back and not tx.committed
        inv.assert_not_called()

    def test_failure_response_does_not_leak_details(self, client):
        tx = _FakeTx(fail_on_insert=True)
        resp, *_ = self._post(client, tx=tx)
        assert "connection dropped" not in resp.get_data(as_text=True)

    def test_insufficient_stock_returns_400_and_records_no_sale(self, client):
        low = {"quality_1": 1, "quality_2": 0, "quality_3": 0}
        tx = _FakeTx(updated=0, stock=low)
        resp, tx, inv = self._post(client, self._valid_body(q1_sold=100), tx=tx)
        assert resp.status_code == 400
        err = resp.get_json()["error"]
        assert err["code"] == "INSUFFICIENT_STOCK" and "q1=1" in err["message"]
        assert not any("INSERT INTO sales" in s for s, _ in tx.statements)
        assert tx.rolled_back and not tx.committed
        inv.assert_not_called()

    def test_no_stock_record_sale_allowed(self, client):
        """No seedlings row at all: the sale is still recorded (unchanged behaviour)."""
        tx = _FakeTx(updated=0, stock=None)
        resp, tx, _ = self._post(client, tx=tx)
        assert resp.status_code == 200
        assert any("INSERT INTO sales" in s for s, _ in tx.statements)

    def test_type_not_found_returns_404_before_any_write(self, client):
        resp, tx, _ = self._post(client, owner=None)
        assert resp.status_code == 404
        assert resp.get_json()["error"]["code"] == "NOT_FOUND"
        assert tx.statements == []

    def test_type_ownership_is_checked_for_the_given_user_and_category(self, client):
        with patch("api.sales.fetch_one", return_value=TYPE_ROW) as owner, \
             patch("api.sales.transaction", return_value=_FakeTx()), \
             patch("api.sales.invalidate_dashboard_cache"):
            client.post(self.URL, json=self._valid_body(), headers=API_H)
        assert owner.call_args[0][1] == (10, 1, TEST_U_ID)

    def test_zero_quantities_accepted(self, client):
        resp, *_ = self._post(client, self._valid_body(q1_sold=0, q2_sold=0, q3_sold=0))
        assert resp.status_code == 200

    def test_price_zero_accepted(self, client):
        resp, *_ = self._post(client, self._valid_body(price=0))
        assert resp.status_code == 200

    # --- validation (400, never an unhandled exception) --------------------------------

    @pytest.mark.parametrize("field", ["u_id", "c_id", "t_id"])
    def test_missing_ids_return_400(self, client, field):
        body = self._valid_body()
        del body[field]
        resp, tx, _ = self._post(client, body)
        assert resp.status_code == 400 and tx.statements == []

    @pytest.mark.parametrize("field", ["q1_sold", "q2_sold", "q3_sold"])
    @pytest.mark.parametrize("bad", ["abc", 1.5, True, [1], 10**10])
    def test_bad_quantities_return_400_not_500(self, client, field, bad):
        resp, tx, _ = self._post(client, self._valid_body(**{field: bad}))
        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "INVALID_QUANTITY"
        assert tx.statements == []

    def test_negative_quantities_cannot_be_used_to_add_stock_through_a_sale(self, client):
        resp, tx, _ = self._post(client, self._valid_body(q1_sold=-50))
        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "INVALID_QUANTITY"
        assert tx.statements == []

    @pytest.mark.parametrize("price", ["invalid", None, True, [1], -1, 10**13])
    def test_bad_price_returns_400(self, client, price):
        resp, tx, _ = self._post(client, self._valid_body(price=price))
        assert resp.status_code == 400
        assert tx.statements == []

    def test_string_u_id_returns_400(self, client):
        resp, *_ = self._post(client, self._valid_body(u_id="abc"))
        assert resp.status_code == 400

    def test_no_api_key_returns_401(self, client):
        assert client.post(self.URL, json=self._valid_body()).status_code == 401

    def test_web_client_cannot_record_sales_for_arbitrary_users(self, client):
        resp = client.post(self.URL, json=self._valid_body(), headers=WEB_HEADERS)
        assert resp.status_code == 401

    def test_ownership_lookup_failure_returns_generic_500(self, client):
        with patch("api.sales.fetch_one", side_effect=RuntimeError("dsn=postgres://u:hunter2@db")):
            resp = client.post(self.URL, json=self._valid_body(), headers=API_H)
        assert resp.status_code == 500
        assert "hunter2" not in resp.get_data(as_text=True)


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
