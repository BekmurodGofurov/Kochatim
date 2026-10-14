"""
Integration tests — api/seedlings.py
Ko'chat zahirasi endpointlari: count, set, get, update
"""
from unittest.mock import patch

import pytest

from conftest import TEST_API_KEY, TEST_TOKEN, TEST_U_ID, FAKE_SEEDLING_ROW, NOW
from conftest import SESSION_HEADERS, WEB_HEADERS

API_H = {"X-API-KEY": TEST_API_KEY, "Content-Type": "application/json"}
SESSION_H = dict(SESSION_HEADERS)

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


LEVELS = {"quality_1": 100, "quality_2": 50, "quality_3": 25}


def _run_sql_on_sqlite(sql, params, start):
    """
    Execute the handler's real UPDATE against an in-memory SQLite table.

    Not Postgres, but the statement is plain SQL (UPDATE ... WHERE ... BETWEEN
    ... RETURNING), so this shows what the guard *does*: a change that would
    leave a level negative matches no row. Returns the RETURNING row or None.
    """
    import sqlite3
    db = sqlite3.connect(":memory:")
    db.execute("CREATE TABLE seedlings (s_id INTEGER PRIMARY KEY, u_id BIGINT, t_id INTEGER, "
               "quality_1 INTEGER, quality_2 INTEGER, quality_3 INTEGER)")
    db.execute("INSERT INTO seedlings VALUES (1, ?, 10, ?, ?, ?)", (TEST_U_ID, *start))
    return db, db.execute(sql.replace("%s", "?"), params).fetchone()


class TestSeedlingsSet:
    URL = "/api/seedlings/set"
    BODY = {"u_id": TEST_U_ID, "t_id": 10, "quality_1": 10, "quality_2": 5, "quality_3": 2}

    def _post(self, client, body=None, *, updated=LEVELS, exists=True):
        with patch("api.seedlings.execute_returning", return_value=updated) as upd, \
             patch("api.seedlings.fetch_one", return_value={"s_id": 1} if exists else None) as look, \
             patch("api.seedlings.execute") as ins, \
             patch("api.seedlings.invalidate_dashboard_cache") as inv:
            resp = client.post(self.URL, json=self.BODY if body is None else body, headers=API_H)
        return resp, upd, look, ins, inv

    def test_update_existing_record(self, client):
        resp, upd, look, ins, inv = self._post(client)
        assert resp.status_code == 200 and resp.get_json()["data"]["saved"] is True
        ins.assert_not_called()
        inv.assert_called_once_with(TEST_U_ID)

    def test_insert_new_record(self, client):
        resp, upd, look, ins, inv = self._post(client, updated=None, exists=False)
        assert resp.status_code == 200
        assert "INSERT INTO seedlings" in ins.call_args[0][0]
        assert ins.call_args[0][1] == (TEST_U_ID, 10, 10, 5, 2)
        inv.assert_called_once_with(TEST_U_ID)

    def test_default_zero_quantities(self, client):
        resp, upd, *_ = self._post(client, {"u_id": TEST_U_ID, "t_id": 10})
        assert resp.status_code == 200
        assert upd.call_args[0][1][:3] == (0, 0, 0)

    def test_the_change_is_applied_in_a_single_guarded_statement(self, client):
        _, upd, look, *_ = self._post(client)
        sql, params = upd.call_args[0]
        assert "UPDATE seedlings" in sql and "BETWEEN 0 AND" in sql and "RETURNING" in sql
        assert params[:5] == (10, 5, 2, TEST_U_ID, 10)
        look.assert_not_called()  # no read-then-write window

    def test_a_correction_that_would_go_negative_is_refused(self, client):
        with patch("api.seedlings.execute_returning", return_value=None), \
             patch("api.seedlings.fetch_one", side_effect=[{"s_id": 1}, {"quality_1": 3, "quality_2": 0, "quality_3": 0}]), \
             patch("api.seedlings.execute") as ins, \
             patch("api.seedlings.invalidate_dashboard_cache") as inv:
            resp = client.post(self.URL, json={**self.BODY, "quality_1": -50}, headers=API_H)
        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "INSUFFICIENT_STOCK"
        ins.assert_not_called()
        inv.assert_not_called()

    def test_negative_first_entry_is_refused(self, client):
        resp, upd, look, ins, inv = self._post(client, {**self.BODY, "quality_2": -1}, updated=None, exists=False)
        assert resp.status_code == 400
        ins.assert_not_called()

    @pytest.mark.parametrize("bad", ["abc", 1.5, True, [1], {"a": 1}, 10**10, "1e3", float("nan")])
    def test_non_numeric_or_absurd_quantities_return_400_not_500(self, client, bad):
        resp, upd, look, ins, inv = self._post(client, {**self.BODY, "quality_1": bad})
        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "INVALID_QUANTITY"
        upd.assert_not_called()

    @pytest.mark.parametrize("ok_value", [7, "7", 7.0, " 7 ", None, ""])
    def test_reasonable_spellings_of_a_number_are_accepted(self, client, ok_value):
        resp, *_ = self._post(client, {**self.BODY, "quality_1": ok_value})
        assert resp.status_code == 200

    def test_missing_u_id_returns_400(self, client):
        assert client.post(self.URL, json={"t_id": 10}, headers=API_H).status_code == 400

    def test_missing_t_id_returns_400(self, client):
        assert client.post(self.URL, json={"u_id": TEST_U_ID}, headers=API_H).status_code == 400

    def test_string_u_id_returns_400(self, client):
        assert client.post(self.URL, json={"u_id": "abc", "t_id": 10}, headers=API_H).status_code == 400

    def test_no_api_key_returns_401(self, client):
        assert client.post(self.URL, json={"u_id": TEST_U_ID, "t_id": 10}).status_code == 401

    def test_database_failure_returns_generic_500(self, client):
        with patch("api.seedlings.execute_returning", side_effect=RuntimeError("dsn=postgres://u:hunter2@db")):
            resp = client.post(self.URL, json=self.BODY, headers=API_H)
        assert resp.status_code == 500
        assert "hunter2" not in resp.get_data(as_text=True)


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

    def _post(self, client, body, *, updated=LEVELS, exists=True, existing_levels=None):
        look = {"s_id": 1, **(existing_levels or LEVELS)} if exists else None
        with patch("api.seedlings.execute_returning", return_value=updated) as upd, \
             patch("api.seedlings.fetch_one", return_value=look) as lookup, \
             patch("api.seedlings.execute") as ex, \
             patch("api.seedlings.invalidate_dashboard_cache") as inv:
            resp = client.post(self.URL, json=body, headers=SESSION_H)
        return resp, upd, lookup, ex, inv

    # --- success -------------------------------------------------------------------

    def test_success_add_stock(self, client, mock_session):
        resp, upd, _, ex, inv = self._post(client, {"t_id": 10, "change_q1": 10, "change_q2": 5, "change_q3": 0})
        assert resp.status_code == 200
        assert resp.get_json()["data"]["saved"] is True
        inv.assert_called_once_with(TEST_U_ID)

    def test_success_deduct_stock(self, client, mock_session):
        resp, *_ = self._post(client, {"t_id": 10, "change_q1": -10, "change_q2": -5, "change_q3": 0})
        assert resp.status_code == 200

    def test_zero_changes_accepted(self, client, mock_session):
        resp, *_ = self._post(client, {"t_id": 10, "change_q1": 0, "change_q2": 0, "change_q3": 0})
        assert resp.status_code == 200

    def test_log_entry_created(self, client, mock_session):
        resp, _, _, ex, _ = self._post(client, {"t_id": 10, "change_q1": 5, "comment": "Test log"})
        assert resp.status_code == 200
        # The stock UPDATE is execute_returning now; execute is the log INSERT alone.
        assert ex.call_count == 1
        sql, params = ex.call_args[0]
        assert "INSERT INTO seedlings_logs" in sql
        assert params == (TEST_U_ID, 10, 5, 0, 0, 0, "Test log")

    def test_first_entry_for_a_variety_inserts_a_row_and_a_log(self, client, mock_session):
        resp, _, _, ex, _ = self._post(client, {"t_id": 10, "change_q1": 5}, updated=None, exists=False)
        assert resp.status_code == 200
        assert [("INSERT INTO seedlings (" in c[0][0]) or ("seedlings_logs" in c[0][0])
                for c in ex.call_args_list] == [True, True]

    # --- the race (hacking_map_advanced E1) -----------------------------------------------

    def test_the_stock_change_is_one_guarded_statement_with_no_read_before_it(self, client, mock_session):
        _, upd, lookup, *_ = self._post(client, {"t_id": 10, "change_q1": -50})
        sql, params = upd.call_args[0]
        assert "UPDATE seedlings" in sql and "BETWEEN 0 AND" in sql and "RETURNING" in sql
        assert params[:5] == (-50, 0, 0, TEST_U_ID, 10)
        lookup.assert_not_called()  # the old SELECT-check-UPDATE window is gone

    def test_two_parallel_removals_cannot_both_succeed(self, client, mock_session):
        """60 in stock, two requests of -50: exactly one may go through."""
        with patch("api.seedlings.execute_returning", return_value=LEVELS) as upd, \
             patch("api.seedlings.execute"), patch("api.seedlings.invalidate_dashboard_cache"):
            client.post(self.URL, json={"t_id": 10, "change_q1": -50}, headers=SESSION_H)
        sql, params = upd.call_args[0]

        db, first = _run_sql_on_sqlite(sql, params, start=(60, 0, 0))
        assert first == (10, 0, 0)                       # the first one lands
        second = db.execute(sql.replace("%s", "?"), params).fetchone()
        assert second is None                            # the second matches no row
        assert db.execute("SELECT quality_1 FROM seedlings").fetchone() == (10,)  # never -40

    @pytest.mark.parametrize("start,change,allowed", [
        ((60, 0, 0), (-60, 0, 0), True),     # exactly to zero is fine
        ((60, 0, 0), (-61, 0, 0), False),
        ((0, 0, 0), (0, 0, -1), False),
        ((5, 5, 5), (-5, -5, -5), True),
        ((5, 5, 5), (-5, -5, -6), False),    # one bad level blocks the whole change
        ((5, 5, 5), (10, 10, 10), True),
        ((1_999_999_999, 0, 0), (2, 0, 0), False),  # would overflow the INTEGER column
    ])
    def test_the_guard_accepts_exactly_the_changes_that_keep_stock_valid(self, client, mock_session, start, change, allowed):
        with patch("api.seedlings.execute_returning", return_value=LEVELS) as upd, \
             patch("api.seedlings.execute"), patch("api.seedlings.invalidate_dashboard_cache"):
            client.post(self.URL, json={"t_id": 10, "change_q1": change[0],
                                        "change_q2": change[1], "change_q3": change[2]}, headers=SESSION_H)
        sql, params = upd.call_args[0]
        _, row = _run_sql_on_sqlite(sql, params, start=start)
        assert (row is not None) is allowed

    # --- refusals ---------------------------------------------------------------------------

    def test_insufficient_stock_returns_400_with_the_current_levels(self, client, mock_session):
        resp, _, _, ex, inv = self._post(
            client, {"t_id": 10, "change_q1": -100}, updated=None,
            existing_levels={"quality_1": 5, "quality_2": 3, "quality_3": 1})
        assert resp.status_code == 400
        err = resp.get_json()["error"]
        assert err["code"] == "INSUFFICIENT_STOCK"
        assert "q1=5" in err["message"] and "q2=3" in err["message"]
        ex.assert_not_called()   # no log entry for a change that did not happen
        inv.assert_not_called()

    def test_negative_first_entry_returns_400(self, client, mock_session):
        resp, _, _, ex, _ = self._post(client, {"t_id": 10, "change_q1": -5}, updated=None, exists=False)
        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "INSUFFICIENT_STOCK"
        ex.assert_not_called()

    # --- input validation ----------------------------------------------------------------------

    def test_missing_t_id_returns_400(self, client, mock_session):
        assert client.post(self.URL, json={"change_q1": 10}, headers=SESSION_H).status_code == 400

    def test_string_t_id_returns_400(self, client, mock_session):
        assert client.post(self.URL, json={"t_id": "abc"}, headers=SESSION_H).status_code == 400

    @pytest.mark.parametrize("field", ["change_q1", "change_q2", "change_q3"])
    @pytest.mark.parametrize("bad", ["abc", 1.5, True, [1], {"a": 1}, 10**10, -(10**10)])
    def test_non_numeric_or_absurd_changes_return_400_not_500(self, client, mock_session, field, bad):
        resp, upd, *_ = self._post(client, {"t_id": 10, field: bad})
        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "INVALID_QUANTITY"
        upd.assert_not_called()

    @pytest.mark.parametrize("price", [-1, "free", True, [1], 10**13, float("nan")])
    def test_invalid_price_returns_400(self, client, mock_session, price):
        resp, upd, *_ = self._post(client, {"t_id": 10, "change_q1": 1, "price": price})
        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "INVALID_PRICE"
        upd.assert_not_called()

    @pytest.mark.parametrize("comment", [123, ["x"], {"a": 1}, "x" * 1001])
    def test_invalid_comment_returns_400(self, client, mock_session, comment):
        resp, upd, *_ = self._post(client, {"t_id": 10, "change_q1": 1, "comment": comment})
        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "INVALID_COMMENT"

    def test_valid_price_and_missing_comment_are_fine(self, client, mock_session):
        resp, *_ = self._post(client, {"t_id": 10, "change_q1": 1, "price": 1500.5})
        assert resp.status_code == 200

    # --- identity -------------------------------------------------------------------------------

    def test_the_user_is_taken_from_the_session_not_the_body(self, client, mock_session):
        _, upd, _, ex, _ = self._post(client, {"t_id": 10, "change_q1": 1, "u_id": 1})
        assert upd.call_args[0][1][3] == TEST_U_ID
        assert 1 not in ex.call_args[0][1][:1]

    def test_no_auth_returns_401(self, client):
        assert client.post(self.URL, json={"t_id": 10}).status_code == 401

    def test_database_failure_returns_generic_500(self, client, mock_session):
        with patch("api.seedlings.execute_returning", side_effect=RuntimeError("dsn=postgres://u:hunter2@db")):
            resp = client.post(self.URL, json={"t_id": 10, "change_q1": 1}, headers=SESSION_H)
        assert resp.status_code == 500
        assert "hunter2" not in resp.get_data(as_text=True)


