"""
Integration tests — auth/ blueprinti
/auth/request-code, /auth/verify-code, /auth/telegram-webapp
and the removal of /auth/user-id-login.

Every login now ends in auth.session_service.create_session, and every login
request must carry the browser's public device key. Route tests stub
create_session; its own behaviour is covered in test_session_service.py.
"""
import hashlib
import time
from unittest.mock import patch

import pytest

from conftest import (
    TEST_API_KEY,
    TEST_BOT_TOKEN,
    TEST_OTP_CODE,
    TEST_U_ID,
    TEST_WEB_KEY,
    FAKE_LOGIN_CODE,
    WEB_HEADERS,
    build_valid_init_data,
    make_device_key,
)

API_KEY_H = {"X-API-KEY": TEST_API_KEY, "Content-Type": "application/json"}

_, DEVICE_JWK = make_device_key()


def _code_hash(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def _canonical(jwk):
    from utils.device_proof import normalize_public_jwk
    return normalize_public_jwk(jwk)


# ─── POST /auth/request-code (bot) ───────────────────────────────────────────

class TestRequestCode:
    URL = "/auth/request-code"

    def _call(self, client, body=None, headers=API_KEY_H):
        body = {"u_id": TEST_U_ID} if body is None else body
        with patch("auth.otp.execute") as mock_exec, \
             patch("auth.otp.fetch_one", return_value=None):
            resp = client.post(self.URL, json=body, headers=headers)
        return resp, mock_exec

    def test_success_returns_code_and_expires_in(self, client):
        resp, _ = self._call(client)
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert len(data["code"]) == 6 and data["code"].isdigit()
        assert data["expires_in"] == 120

    def test_only_the_hash_of_the_code_is_stored(self, client):
        resp, mock_exec = self._call(client)
        code = resp.get_json()["data"]["code"]
        insert = [c for c in mock_exec.call_args_list if "INSERT INTO login_codes" in c[0][0]][0]
        assert insert[0][1][0] == _code_hash(code)
        assert code not in repr(insert)

    def test_retires_the_users_earlier_unused_codes(self, client):
        _, mock_exec = self._call(client)
        sqls = [c[0][0] for c in mock_exec.call_args_list]
        retire = next(i for i, s in enumerate(sqls) if "UPDATE login_codes SET used_at" in s)
        insert = next(i for i, s in enumerate(sqls) if "INSERT INTO login_codes" in s)
        assert retire < insert  # old codes die before the new one exists

    def test_code_that_clashes_with_a_live_one_is_regenerated(self, client):
        """verify-code looks a code up by hash alone, so two live users must never share one."""
        with patch("auth.otp.execute"), \
             patch("auth.otp.generate_otp_6", side_effect=["111111", "222222"]), \
             patch("auth.otp.fetch_one", side_effect=[{"taken": 1}, None]):
            resp = client.post(self.URL, json={"u_id": TEST_U_ID}, headers=API_KEY_H)
        assert resp.get_json()["data"]["code"] == "222222"

    def test_gives_up_with_500_if_no_unique_code_can_be_found(self, client):
        with patch("auth.otp.execute"), patch("auth.otp.fetch_one", return_value={"taken": 1}):
            resp = client.post(self.URL, json={"u_id": TEST_U_ID}, headers=API_KEY_H)
        assert resp.status_code == 500
        assert resp.get_json()["error"]["message"] == "Server error"

    def test_optional_fields_accepted(self, client):
        resp, _ = self._call(client, {"u_id": TEST_U_ID, "u_name": "Ali", "u_username": "ali",
                                      "u_phone": "+998901234567", "u_age": 30})
        assert resp.status_code == 200

    @pytest.mark.parametrize("u_id", [None, "not_int", 1.5, [1], {"a": 1}])
    def test_bad_u_id_returns_400(self, client, u_id):
        resp, mock_exec = self._call(client, {"u_id": u_id})
        assert resp.status_code == 400
        mock_exec.assert_not_called()

    def test_missing_u_id_returns_400(self, client):
        resp, _ = self._call(client, {})
        assert resp.status_code == 400

    def test_no_api_key_returns_401(self, client):
        resp, mock_exec = self._call(client, headers={"Content-Type": "application/json"})
        assert resp.status_code == 401
        mock_exec.assert_not_called()

    def test_wrong_api_key_returns_401(self, client):
        resp, _ = self._call(client, headers={"X-API-KEY": "nope", "Content-Type": "application/json"})
        assert resp.status_code == 401

    def test_web_client_key_cannot_request_codes(self, client):
        """The web key is public; if it could mint codes it would be a master key."""
        resp, mock_exec = self._call(client, headers=WEB_HEADERS)
        assert resp.status_code == 401
        mock_exec.assert_not_called()

    def test_db_failure_returns_generic_500(self, client):
        with patch("auth.otp.execute", side_effect=RuntimeError("dsn=postgres://u:hunter2@db")):
            resp = client.post(self.URL, json={"u_id": TEST_U_ID}, headers=API_KEY_H)
        assert resp.status_code == 500
        assert "hunter2" not in resp.get_data(as_text=True)


# ─── POST /auth/verify-code (web) ────────────────────────────────────────────

class TestVerifyCode:
    URL = "/auth/verify-code"

    def _post(self, client, body, headers=None, ip=None):
        headers = dict(WEB_HEADERS if headers is None else headers)
        if ip:
            headers["X-Real-IP"] = ip  # honoured: the test client's peer is 127.0.0.1
        return client.post(self.URL, json=body, headers=headers)

    def _login(self, client, code=TEST_OTP_CODE, ip=None, **mocks):
        """A successful-looking login with every DB touch stubbed."""
        row = mocks.get("row", {**FAKE_LOGIN_CODE, "code_hash": _code_hash(code)})
        with patch("auth.otp.fetch_one", return_value=row), \
             patch("auth.otp.execute_returning", return_value=mocks.get("spent", {"u_id": TEST_U_ID})), \
             patch("auth.otp.create_session", return_value="the-session-token") as cs:
            resp = self._post(client, {"code": code, "device_key": DEVICE_JWK}, ip=ip)
        return resp, cs

    # --- success -----------------------------------------------------------

    def test_success_returns_session_token(self, client):
        resp, _ = self._login(client)
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["session_token"] == "the-session-token"
        assert data["u_id"] == TEST_U_ID
        assert data["expires_in"] > 0

    def test_session_is_bound_to_the_submitted_device_key(self, client):
        _, create_session = self._login(client)
        create_session.assert_called_once_with(TEST_U_ID, _canonical(DEVICE_JWK))

    def test_code_is_spent_in_one_atomic_statement(self, client):
        with patch("auth.otp.fetch_one", return_value={**FAKE_LOGIN_CODE}), \
             patch("auth.otp.execute_returning", return_value={"u_id": TEST_U_ID}) as spend, \
             patch("auth.otp.execute") as plain_exec, \
             patch("auth.otp.create_session", return_value="t"):
            self._post(client, {"code": TEST_OTP_CODE, "device_key": DEVICE_JWK})
        sql = spend.call_args[0][0]
        assert "UPDATE login_codes" in sql and "used_at IS NULL" in sql and "RETURNING" in sql
        plain_exec.assert_not_called()  # no separate, racy UPDATE

    def test_logs_in_the_owner_of_the_code_not_a_body_field(self, client):
        with patch("auth.otp.fetch_one", return_value={**FAKE_LOGIN_CODE}), \
             patch("auth.otp.execute_returning", return_value={"u_id": 777}), \
             patch("auth.otp.create_session", return_value="t") as cs:
            resp = self._post(client, {"code": TEST_OTP_CODE, "device_key": DEVICE_JWK, "u_id": 1})
        assert resp.get_json()["data"]["u_id"] == 777
        assert cs.call_args[0][0] == 777

    # --- the device key is mandatory ----------------------------------------

    @pytest.mark.parametrize("bad_key", [
        None, "", "string", 42, [], {},
        {"kty": "RSA", "n": "x", "e": "AQAB"},
        {"kty": "EC", "crv": "P-384", "x": DEVICE_JWK["x"], "y": DEVICE_JWK["y"]},
        {**DEVICE_JWK, "d": "c2VjcmV0LXByaXZhdGUtcGFydA"},     # a private key was sent
        {**DEVICE_JWK, "x": "AAAA"},                          # coordinate too short
        {"kty": "EC", "crv": "P-256", "x": DEVICE_JWK["x"], "y": DEVICE_JWK["x"]},  # not on the curve
    ])
    def test_missing_or_invalid_device_key_returns_400(self, client, bad_key):
        with patch("auth.otp.fetch_one") as lookup, patch("auth.otp.create_session") as cs:
            resp = self._post(client, {"code": TEST_OTP_CODE, "device_key": bad_key})
        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "DEVICE_KEY_REQUIRED"
        cs.assert_not_called()
        lookup.assert_not_called()  # ...and the one-time code was never touched

    def test_request_without_device_key_does_not_burn_the_code(self, client):
        with patch("auth.otp.fetch_one") as lookup, patch("auth.otp.execute_returning") as spend:
            self._post(client, {"code": TEST_OTP_CODE})
        lookup.assert_not_called()
        spend.assert_not_called()

    # --- code validation ----------------------------------------------------

    @pytest.mark.parametrize("code", ["", "12345", "1234567", "abcdef", "12 456", None, 123456, ["1"], {"a": 1}])
    def test_malformed_code_returns_400(self, client, code):
        resp = self._post(client, {"code": code, "device_key": DEVICE_JWK})
        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "INVALID_CODE"

    def test_missing_code_returns_400(self, client):
        resp = self._post(client, {"device_key": DEVICE_JWK})
        assert resp.status_code == 400

    def test_code_not_found_returns_400(self, client):
        with patch("auth.otp.fetch_one", return_value=None):
            resp = self._post(client, {"code": "999999", "device_key": DEVICE_JWK})
        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "CODE_NOT_FOUND"

    def test_expired_code_returns_400(self, client):
        row = {**FAKE_LOGIN_CODE, "expires_at": datetime_past()}
        resp, cs = self._login(client, row=row)
        assert resp.get_json()["error"]["code"] == "CODE_EXPIRED"
        cs.assert_not_called()

    def test_already_used_code_returns_400(self, client):
        row = {**FAKE_LOGIN_CODE, "used_at": datetime_past()}
        resp, cs = self._login(client, row=row)
        assert resp.get_json()["error"]["code"] == "CODE_USED"
        cs.assert_not_called()

    def test_losing_the_race_for_a_code_gets_no_session(self, client):
        """Two parallel requests both read the code as unused; only one UPDATE matches."""
        resp, cs = self._login(client, spent=None)
        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "CODE_USED"
        cs.assert_not_called()

    # --- rate limiting ------------------------------------------------------

    def _fail(self, client, ip):
        with patch("auth.otp.fetch_one", return_value=None):
            return self._post(client, {"code": "999999", "device_key": DEVICE_JWK}, ip=ip)

    def test_five_wrong_codes_lock_that_ip_out(self, client):
        for _ in range(5):
            assert self._fail(client, "198.51.100.5").status_code == 400
        resp = self._fail(client, "198.51.100.5")
        assert resp.status_code == 429
        assert resp.get_json()["error"]["code"] == "RATE_LIMITED"
        assert int(resp.headers["Retry-After"]) > 0

    def test_a_locked_out_ip_cannot_succeed_even_with_the_right_code(self, client):
        for _ in range(5):
            self._fail(client, "198.51.100.5")
        resp, cs = self._login(client, ip="198.51.100.5")
        assert resp.status_code == 429
        cs.assert_not_called()

    def test_lockout_is_per_ip(self, client):
        for _ in range(5):
            self._fail(client, "198.51.100.5")
        resp, _ = self._login(client, ip="198.51.100.99")
        assert resp.status_code == 200

    def test_successful_logins_do_not_count_against_the_limit(self, client):
        """A campus behind one NAT must not lock itself out by logging in correctly."""
        for _ in range(8):
            resp, _ = self._login(client, ip="198.51.100.5")
            assert resp.status_code == 200

    def test_malformed_codes_do_not_count_either(self, client):
        for _ in range(10):
            self._post(client, {"code": "abc", "device_key": DEVICE_JWK}, ip="198.51.100.5")
        resp, _ = self._login(client, ip="198.51.100.5")
        assert resp.status_code == 200

    def test_spoofed_x_forwarded_for_does_not_dodge_the_limit(self, client):
        for i in range(5):
            with patch("auth.otp.fetch_one", return_value=None):
                client.post(self.URL, json={"code": "999999", "device_key": DEVICE_JWK},
                            headers={**WEB_HEADERS, "X-Real-IP": "198.51.100.5",
                                     "X-Forwarded-For": f"10.9.9.{i}"})
        with patch("auth.otp.fetch_one", return_value=None):
            resp = client.post(self.URL, json={"code": "999999", "device_key": DEVICE_JWK},
                               headers={**WEB_HEADERS, "X-Real-IP": "198.51.100.5",
                                        "X-Forwarded-For": "10.9.9.200"})
        assert resp.status_code == 429

    def test_global_limit_stops_guessing_spread_over_many_ips(self, client):
        with patch("auth.otp._FAIL_LIMIT_GLOBAL", 3):
            for i in range(3):
                self._fail(client, f"198.51.100.{i + 1}")
            resp = self._fail(client, "198.51.100.77")
        assert resp.status_code == 429

    def test_redis_down_refuses_login_instead_of_allowing_unlimited_guesses(self, client):
        with patch("auth.otp.ratelimit.count", return_value=None), \
             patch("auth.otp.fetch_one") as lookup:
            resp = self._post(client, {"code": TEST_OTP_CODE, "device_key": DEVICE_JWK})
        assert resp.status_code == 503
        assert resp.get_json()["error"]["code"] == "UNAVAILABLE"
        lookup.assert_not_called()

    def test_redis_failing_while_recording_a_miss_still_answers_cleanly(self, client):
        with patch("auth.otp.ratelimit.record", return_value=None), \
             patch("auth.otp.fetch_one", return_value=None):
            resp = self._post(client, {"code": "999999", "device_key": DEVICE_JWK})
        assert resp.status_code == 400

    # --- gate and failure modes ----------------------------------------------

    def test_requires_the_client_key(self, client):
        resp = client.post(self.URL, json={"code": TEST_OTP_CODE, "device_key": DEVICE_JWK})
        assert resp.status_code == 401

    def test_db_failure_returns_generic_500(self, client):
        with patch("auth.otp.fetch_one", side_effect=RuntimeError("dsn=postgres://u:hunter2@db")):
            resp = self._post(client, {"code": TEST_OTP_CODE, "device_key": DEVICE_JWK})
        assert resp.status_code == 500
        assert "hunter2" not in resp.get_data(as_text=True)

    def test_session_creation_failure_returns_generic_500(self, client):
        with patch("auth.otp.fetch_one", return_value={**FAKE_LOGIN_CODE}), \
             patch("auth.otp.execute_returning", return_value={"u_id": TEST_U_ID}), \
             patch("auth.otp.create_session", side_effect=RuntimeError("dsn=postgres://u:hunter2@db")):
            resp = self._post(client, {"code": TEST_OTP_CODE, "device_key": DEVICE_JWK})
        assert resp.status_code == 500
        assert "hunter2" not in resp.get_data(as_text=True)


def datetime_past():
    from datetime import datetime
    return datetime(2000, 1, 1)


# ─── POST /auth/telegram-webapp (web) ────────────────────────────────────────

class TestTelegramWebapp:
    URL = "/auth/telegram-webapp"

    def _post(self, client, body):
        return client.post(self.URL, json=body, headers=WEB_HEADERS)

    def _login(self, client, init_data=None, user_row=None, **body):
        init_data = init_data or build_valid_init_data(TEST_BOT_TOKEN, TEST_U_ID)
        payload = {"initData": init_data, "device_key": DEVICE_JWK, **body}
        with patch("auth.telegram_webapp.execute"), \
             patch("auth.telegram_webapp.fetch_one", return_value=user_row or {"u_phone": "+998901234567"}), \
             patch("auth.telegram_webapp.create_session", return_value="the-session-token") as cs:
            resp = self._post(client, payload)
        return resp, cs

    def test_success_returns_session_token(self, client):
        resp, _ = self._login(client)
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["session_token"] == "the-session-token"
        assert data["u_id"] == TEST_U_ID

    def test_session_is_bound_to_the_submitted_device_key(self, client):
        _, cs = self._login(client)
        cs.assert_called_once_with(TEST_U_ID, _canonical(DEVICE_JWK))

    def test_logs_in_the_telegram_user_not_a_body_field(self, client):
        _, cs = self._login(client, u_id=1)
        assert cs.call_args[0][0] == TEST_U_ID

    def test_is_registered_true_when_phone_exists(self, client):
        resp, _ = self._login(client, user_row={"u_phone": "+998901111111"})
        assert resp.get_json()["data"]["is_registered"] is True

    def test_is_registered_false_when_no_phone(self, client):
        resp, _ = self._login(client, user_row={"u_phone": None})
        assert resp.get_json()["data"]["is_registered"] is False

    @pytest.mark.parametrize("bad_key", [None, "", {}, {"kty": "EC"}, {**DEVICE_JWK, "d": "x"}])
    def test_missing_or_invalid_device_key_returns_400(self, client, bad_key):
        init_data = build_valid_init_data(TEST_BOT_TOKEN, TEST_U_ID)
        with patch("auth.telegram_webapp.create_session") as cs:
            resp = self._post(client, {"initData": init_data, "device_key": bad_key})
        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "DEVICE_KEY_REQUIRED"
        cs.assert_not_called()

    def test_invalid_init_data_returns_401(self, client):
        with patch("auth.telegram_webapp.create_session") as cs:
            resp = self._post(client, {"initData": "invalid&data", "device_key": DEVICE_JWK})
        assert resp.status_code == 401
        assert resp.get_json()["error"]["code"] == "INVALID_INITDATA"
        cs.assert_not_called()

    @pytest.mark.parametrize("init_data", [None, "", 123, [], {"a": 1}])
    def test_missing_or_non_string_init_data_returns_401(self, client, init_data):
        resp = self._post(client, {"initData": init_data, "device_key": DEVICE_JWK})
        assert resp.status_code == 401

    def test_missing_init_data_returns_401(self, client):
        assert self._post(client, {"device_key": DEVICE_JWK}).status_code == 401

    def test_tampered_hash_returns_401(self, client):
        init_data = build_valid_init_data(TEST_BOT_TOKEN) + "&extra=tamper"
        resp = self._post(client, {"initData": init_data, "device_key": DEVICE_JWK})
        assert resp.status_code == 401

    def test_initdata_signed_with_another_bot_token_returns_401(self, client):
        init_data = build_valid_init_data("999:SOME_OTHER_BOT", TEST_U_ID)
        resp = self._post(client, {"initData": init_data, "device_key": DEVICE_JWK})
        assert resp.status_code == 401

    def test_stale_initdata_is_refused(self, client):
        """A captured initData must not log in forever."""
        old = str(int(time.time()) - 2 * 3600)
        init_data = build_valid_init_data(TEST_BOT_TOKEN, TEST_U_ID, auth_date=old)
        resp, cs = self._login(client, init_data=init_data)
        assert resp.status_code == 401
        assert resp.get_json()["error"]["code"] == "INVALID_INITDATA"
        cs.assert_not_called()

    def test_fresh_initdata_just_inside_the_window_is_accepted(self, client):
        recent = str(int(time.time()) - 3000)
        init_data = build_valid_init_data(TEST_BOT_TOKEN, TEST_U_ID, auth_date=recent)
        resp, _ = self._login(client, init_data=init_data)
        assert resp.status_code == 200

    def test_initdata_from_the_future_is_refused(self, client):
        future = str(int(time.time()) + 3600)
        init_data = build_valid_init_data(TEST_BOT_TOKEN, TEST_U_ID, auth_date=future)
        resp, _ = self._login(client, init_data=init_data)
        assert resp.status_code == 401

    def test_initdata_without_auth_date_is_refused(self, client):
        from urllib.parse import parse_qsl, urlencode
        import hmac as _hmac
        pairs = dict(parse_qsl(build_valid_init_data(TEST_BOT_TOKEN, TEST_U_ID)))
        pairs.pop("auth_date"); pairs.pop("hash")
        check = "\n".join(f"{k}={pairs[k]}" for k in sorted(pairs))
        secret = _hmac.new(b"WebAppData", TEST_BOT_TOKEN.encode(), hashlib.sha256).digest()
        pairs["hash"] = _hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
        resp, _ = self._login(client, init_data=urlencode(pairs))
        assert resp.status_code == 401

    def test_rejection_reason_is_logged_but_not_returned(self, client, caplog):
        import logging
        with caplog.at_level(logging.WARNING):
            resp = self._post(client, {"initData": "a=1&hash=deadbeef", "device_key": DEVICE_JWK})
        assert "invalid hash" in caplog.text
        assert "extra" not in resp.get_json()["error"]
        assert "invalid hash" not in resp.get_data(as_text=True)

    def test_requires_the_client_key(self, client):
        init_data = build_valid_init_data(TEST_BOT_TOKEN, TEST_U_ID)
        resp = client.post(self.URL, json={"initData": init_data, "device_key": DEVICE_JWK})
        assert resp.status_code == 401

    def test_db_failure_returns_generic_500(self, client):
        init_data = build_valid_init_data(TEST_BOT_TOKEN, TEST_U_ID)
        with patch("auth.telegram_webapp.execute", side_effect=RuntimeError("dsn=postgres://u:hunter2@db")):
            resp = self._post(client, {"initData": init_data, "device_key": DEVICE_JWK})
        assert resp.status_code == 500
        assert "hunter2" not in resp.get_data(as_text=True)


# ─── /auth/user-id-login no longer exists ────────────────────────────────────

class TestUserIdLoginIsGone:
    """
    The old endpoint issued a 30-day session for any u_id with no proof of
    anything. A Telegram ID is not a secret, so that was account takeover.
    """
    URL = "/auth/user-id-login"

    @pytest.mark.parametrize("headers", [
        WEB_HEADERS,
        API_KEY_H,
        {"X-API-KEY": TEST_API_KEY, "X-Client-Key": TEST_WEB_KEY, "Content-Type": "application/json"},
    ])
    def test_route_does_not_exist_for_any_caller(self, client, headers):
        with patch("db.execute") as ex, patch("db.fetch_one") as fo:
            resp = client.post(self.URL, json={"u_id": TEST_U_ID}, headers=headers)
        assert resp.status_code == 404
        ex.assert_not_called()
        fo.assert_not_called()

    def test_unauthenticated_caller_cannot_even_tell_it_is_missing(self, client):
        resp = client.post(self.URL, json={"u_id": TEST_U_ID})
        assert resp.status_code == 401

    def test_no_route_in_the_url_map(self, app):
        assert not [r for r in app.url_map.iter_rules() if "user-id-login" in r.rule]

    def test_module_is_gone(self):
        import importlib
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module("auth.user_id_login")

    def test_a_valid_u_id_alone_yields_no_token(self, client):
        with patch("auth.session_service.execute") as ex:
            resp = client.post(self.URL, json={"u_id": TEST_U_ID}, headers=WEB_HEADERS)
        assert "session_token" not in resp.get_data(as_text=True)
        ex.assert_not_called()
