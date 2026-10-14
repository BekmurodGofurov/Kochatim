"""
Unit tests — auth/session_service.py

create_session is the single place a web session is born. Its job here:
store only a hash of the token, bind the session to the browser's key, and take
the IP and browser from the request itself -- there is nowhere to pass them in.
"""
import inspect
from unittest.mock import patch

import pytest

from auth import session_service
from auth.session_service import DeviceKeyError, MAX_SESSIONS, create_session, parse_device_key
from conftest import TEST_U_ID, make_device_key
from utils.device import client_fingerprint, parse_device
from utils.security import sha256_hex

_, JWK = make_device_key()
KEY = parse_device_key(JWK)
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
REAL_IP = "198.51.100.5"


def _ctx(app, headers=None, json=None, remote="127.0.0.1"):
    h = {"User-Agent": UA, "X-Real-IP": REAL_IP}
    h.update(headers or {})
    return app.test_request_context("/auth/verify-code", method="POST", json=json,
                                    headers=h, environ_base={"REMOTE_ADDR": remote})


@pytest.fixture
def db():
    with patch("auth.session_service.execute") as ex, \
         patch("auth.session_service.fetch_all", return_value=[]) as fa, \
         patch("auth.session_service.get_city", return_value="Toshkent") as city:
        yield type("DB", (), {"execute": ex, "fetch_all": fa, "city": city})


def _insert(db):
    return next(c for c in db.execute.call_args_list if "INSERT INTO sessions" in c[0][0])


class TestParseDeviceKey:
    def test_valid_key_returns_canonical_json(self):
        assert '"crv":"P-256"' in parse_device_key(JWK)

    @pytest.mark.parametrize("bad", [None, {}, "x", {"kty": "EC"}, {**JWK, "d": "x"}])
    def test_invalid_key_raises_device_key_error(self, bad):
        with pytest.raises(DeviceKeyError):
            parse_device_key(bad)

    def test_device_key_error_is_a_value_error(self):
        assert issubclass(DeviceKeyError, ValueError)


class TestCreateSession:
    def test_returns_a_long_url_safe_random_token(self, app, db):
        with _ctx(app):
            tokens = {create_session(TEST_U_ID, KEY) for _ in range(20)}
        assert len(tokens) == 20
        for t in tokens:
            assert len(t) >= 43 and all(c.isalnum() or c in "-_" for c in t)

    def test_only_a_hash_of_the_token_is_stored(self, app, db):
        with _ctx(app):
            token = create_session(TEST_U_ID, KEY)
        params = _insert(db)[0][1]
        assert params[0] == sha256_hex(token)
        assert token not in repr(db.execute.call_args_list)

    def test_session_is_bound_to_the_device_key(self, app, db):
        with _ctx(app):
            create_session(TEST_U_ID, KEY)
        sql, params = _insert(db)[0]
        assert "device_key" in sql
        assert KEY in params

    def test_session_records_the_browser_family_for_later_comparison(self, app, db):
        with _ctx(app):
            create_session(TEST_U_ID, KEY)
        assert client_fingerprint(UA) in _insert(db)[0][1]

    def test_ip_and_browser_come_from_the_request(self, app, db):
        with _ctx(app):
            create_session(TEST_U_ID, KEY)
        params = _insert(db)[0][1]
        assert REAL_IP in params
        assert parse_device(UA) in params
        db.city.assert_called_once_with(REAL_IP)
        assert "Toshkent" in params

    def test_body_fields_cannot_set_ip_browser_or_city(self, app, db):
        evil = {"ip": "6.6.6.6", "ip_address": "6.6.6.6", "user_agent": "Hacker/1.0",
                "device_name": "Totally Legit Device", "city": "Sterling", "u_id": 1}
        with _ctx(app, json=evil):
            create_session(TEST_U_ID, KEY)
        params = _insert(db)[0][1]
        flat = repr(params)
        for planted in ("6.6.6.6", "Hacker", "Totally Legit", "Sterling"):
            assert planted not in flat
        assert params[1] == TEST_U_ID

    def test_x_forwarded_for_cannot_set_the_ip(self, app, db):
        with _ctx(app, headers={"X-Forwarded-For": "173.252.64.1"}):
            create_session(TEST_U_ID, KEY)
        params = _insert(db)[0][1]
        assert "173.252.64.1" not in params and REAL_IP in params

    def test_a_direct_caller_cannot_name_its_own_ip(self, app, db):
        """Peer is not our proxy, so X-Real-IP is ignored and the TCP address is recorded."""
        with _ctx(app, remote="203.0.113.9", headers={"X-Real-IP": "6.6.6.6"}):
            create_session(TEST_U_ID, KEY)
        params = _insert(db)[0][1]
        assert "203.0.113.9" in params and "6.6.6.6" not in params

    def test_the_signature_has_no_ip_or_user_agent_parameter(self):
        """Structural guarantee: there is nowhere to pass a caller-chosen value."""
        assert list(inspect.signature(create_session).parameters) == ["u_id", "device_key"]

    def test_expiry_is_in_the_future(self, app, db):
        from datetime import datetime
        with _ctx(app):
            create_session(TEST_U_ID, KEY)
        assert _insert(db)[0][1][2] > datetime.utcnow()

    # --- session cap -----------------------------------------------------------

    def _rows(self, n):
        return [{"token_hash": f"hash{i}"} for i in range(n)]

    def test_keeps_only_the_newest_sessions_and_drops_the_rest(self, app, db):
        db.fetch_all.return_value = self._rows(MAX_SESSIONS + 2)
        with _ctx(app), patch("auth.session_service.invalidate_session_cache") as inv:
            create_session(TEST_U_ID, KEY)
        delete = next(c for c in db.execute.call_args_list if "DELETE FROM sessions" in c[0][0])
        assert delete[0][1] == (TEST_U_ID, [f"hash{i}" for i in range(MAX_SESSIONS)])
        assert [c[0][0] for c in inv.call_args_list] == [f"hash{i}" for i in range(MAX_SESSIONS, MAX_SESSIONS + 2)]

    def test_dropped_sessions_stop_working_immediately_not_after_cache_expiry(self, app, db, redis_conn):
        redis_conn.set("session_hash3", "cached")
        db.fetch_all.return_value = self._rows(MAX_SESSIONS + 1)
        with _ctx(app):
            create_session(TEST_U_ID, KEY)
        assert redis_conn.get("session_hash3") is None

    def test_nothing_is_deleted_under_the_cap(self, app, db):
        db.fetch_all.return_value = self._rows(MAX_SESSIONS)
        with _ctx(app):
            create_session(TEST_U_ID, KEY)
        assert not [c for c in db.execute.call_args_list if "DELETE FROM sessions" in c[0][0]]

    def test_session_list_caches_are_refreshed(self, app, db, redis_conn):
        redis_conn.set(f"sessions_{TEST_U_ID}", "stale")
        redis_conn.set(f"settings_{TEST_U_ID}", "stale")
        with _ctx(app):
            create_session(TEST_U_ID, KEY)
        assert redis_conn.get(f"sessions_{TEST_U_ID}") is None
        assert redis_conn.get(f"settings_{TEST_U_ID}") is None

    # --- failures ---------------------------------------------------------------

    def test_a_failed_insert_raises_and_never_returns_a_token(self, app, db):
        db.execute.side_effect = RuntimeError("db down")
        with _ctx(app), pytest.raises(RuntimeError):
            create_session(TEST_U_ID, KEY)

    def test_geolocation_failure_does_not_block_login(self, app):
        """get_city swallows its own errors; a dead ip-api must not break sign-in."""
        with patch("auth.session_service.execute"), \
             patch("auth.session_service.fetch_all", return_value=[]), \
             patch("utils.device._requests.get", side_effect=OSError("unreachable")), \
             _ctx(app, headers={"X-Real-IP": "8.8.8.8"}):
            assert create_session(TEST_U_ID, KEY)

    def test_module_exposes_no_way_to_mint_a_session_from_a_user_id_alone(self):
        public = [n for n in dir(session_service) if not n.startswith("_")]
        assert "create_session" in public
        assert list(inspect.signature(session_service.create_session).parameters)[1] == "device_key"
