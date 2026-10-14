"""
Integration tests — device-bound sessions, end to end through the real
require_session middleware (no stubbed proof, unlike the route tests).

The scenario these exist for: someone copies `session_token` out of one
browser's localStorage and uses it from somewhere else. The token alone must
get them nothing -- every request also needs a signature from the private key
that never left the original browser.
"""
import time
from unittest.mock import patch

import pytest

from conftest import (
    FAKE_USER,
    TEST_TOKEN,
    TEST_U_ID,
    TEST_WEB_KEY,
    get_test_token_hash,
    make_device_key,
    sign_proof,
)
from utils.device import client_fingerprint
from utils.device_proof import normalize_public_jwk

CHROME_MAC = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
CHROME_MAC_UPDATED = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/131.0.6778.86 Safari/537.36"
FIREFOX_WIN = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0"

OWNER_PRIVATE, OWNER_JWK = make_device_key()
THIEF_PRIVATE, _ = make_device_key()


def _session_row(**over):
    row = {
        "u_id": TEST_U_ID,
        "device_key": normalize_public_jwk(OWNER_JWK),
        "ua_fp": client_fingerprint(CHROME_MAC),
    }
    row.update(over)
    return row


def _headers(proof=None, ua=CHROME_MAC, token=TEST_TOKEN, key=TEST_WEB_KEY):
    h = {"User-Agent": ua}
    if key is not None:
        h["X-Client-Key"] = key
    if token is not None:
        h["Authorization"] = f"Bearer {token}"
    if proof is not None:
        h["X-Session-Proof"] = proof
    return h


@pytest.fixture
def live_session():
    """A session that exists in the database. The cache is the real (fake) Redis."""
    with patch("middleware.require_session.fetch_one", return_value=_session_row()) as db, \
         patch("api.users.fetch_one", return_value=FAKE_USER):
        yield db


class TestDeviceBoundSession:
    URL = "/api/me"

    def _get(self, client, proof, **kw):
        return client.get(self.URL, headers=_headers(proof=proof, **kw))

    # --- the legitimate browser ------------------------------------------------

    def test_valid_token_and_proof_is_accepted(self, client, live_session):
        proof = sign_proof(OWNER_PRIVATE, TEST_TOKEN, "GET", self.URL)
        resp = self._get(client, proof)
        assert resp.status_code == 200
        assert resp.get_json()["data"]["u_id"] == TEST_U_ID

    def test_every_request_needs_its_own_fresh_proof(self, client, live_session):
        for _ in range(3):
            proof = sign_proof(OWNER_PRIVATE, TEST_TOKEN, "GET", self.URL)
            assert self._get(client, proof).status_code == 200

    def test_session_is_cached_but_the_proof_is_still_checked_each_time(self, client, live_session):
        self._get(client, sign_proof(OWNER_PRIVATE, TEST_TOKEN, "GET", self.URL))
        assert self._get(client, None).status_code == 401  # served from cache, still no proof
        assert live_session.call_count == 1

    def test_query_string_is_part_of_what_is_signed(self, client, live_session):
        url = "/api/seedlings?t_id=10"
        with patch("api.seedlings.fetch_one", return_value=None):
            ok = client.get(url, headers=_headers(sign_proof(OWNER_PRIVATE, TEST_TOKEN, "GET", url)))
            tampered = client.get("/api/seedlings?t_id=11",
                                  headers=_headers(sign_proof(OWNER_PRIVATE, TEST_TOKEN, "GET", url)))
        assert ok.status_code == 200
        assert tampered.status_code == 401

    def test_percent_encoded_paths_verify_against_the_raw_request_target(self, client, live_session):
        """
        Flask decodes request.path; the browser signed the encoded form. Behind
        gunicorn the raw target is available as RAW_URI and is what must match.
        """
        raw = "/api/seedlings?t_id=10&note=%D1%88%20x"
        proof = sign_proof(OWNER_PRIVATE, TEST_TOKEN, "GET", raw)
        with patch("api.seedlings.fetch_one", return_value=None):
            resp = client.get(raw, headers=_headers(proof), environ_overrides={"RAW_URI": raw})
        assert resp.status_code == 200

    def test_the_signed_target_must_equal_the_raw_request_target(self, client, live_session):
        """A proof for /api/me does not cover what the wire actually carried if that differs."""
        proof = sign_proof(OWNER_PRIVATE, TEST_TOKEN, "GET", "/api/me")
        resp = client.get(self.URL, headers=_headers(proof), environ_overrides={"RAW_URI": "/api/me?extra=1"})
        assert resp.status_code == 401

    def test_a_browser_update_does_not_log_the_user_out(self, client, live_session):
        proof = sign_proof(OWNER_PRIVATE, TEST_TOKEN, "GET", self.URL)
        assert self._get(client, proof, ua=CHROME_MAC_UPDATED).status_code == 200

    # --- the stolen token --------------------------------------------------------

    def test_token_alone_is_worthless(self, client, live_session):
        """The localStorage copy-paste attack: right token, no key to sign with."""
        resp = self._get(client, None)
        assert resp.status_code == 401
        assert resp.get_json()["error"]["code"] == "UNAUTHORIZED"

    def test_proof_signed_by_the_attackers_own_key_is_rejected(self, client, live_session):
        forged = sign_proof(THIEF_PRIVATE, TEST_TOKEN, "GET", self.URL)
        assert self._get(client, forged).status_code == 401

    def test_a_captured_proof_cannot_be_replayed(self, client, live_session):
        proof = sign_proof(OWNER_PRIVATE, TEST_TOKEN, "GET", self.URL)
        assert self._get(client, proof).status_code == 200
        assert self._get(client, proof).status_code == 401

    def test_a_captured_proof_is_useless_on_another_endpoint(self, client, live_session):
        proof = sign_proof(OWNER_PRIVATE, TEST_TOKEN, "GET", self.URL)
        resp = client.get("/api/sessions", headers=_headers(proof))
        assert resp.status_code == 401

    def test_a_captured_proof_is_useless_with_another_method(self, client, live_session):
        proof = sign_proof(OWNER_PRIVATE, TEST_TOKEN, "GET", "/api/logout")
        resp = client.post("/api/logout", headers=_headers(proof))
        assert resp.status_code == 401

    def test_a_proof_made_for_another_token_is_useless(self, client, live_session):
        proof = sign_proof(OWNER_PRIVATE, "some-other-token", "GET", self.URL)
        assert self._get(client, proof).status_code == 401

    def test_stale_proof_is_rejected(self, client, live_session):
        old_ms = (time.time() - 3600) * 1000
        proof = sign_proof(OWNER_PRIVATE, TEST_TOKEN, "GET", self.URL, ts_ms=old_ms)
        assert self._get(client, proof).status_code == 401

    def test_proof_from_the_future_is_rejected(self, client, live_session):
        future_ms = (time.time() + 3600) * 1000
        proof = sign_proof(OWNER_PRIVATE, TEST_TOKEN, "GET", self.URL, ts_ms=future_ms)
        assert self._get(client, proof).status_code == 401

    @pytest.mark.parametrize("garbage", [
        "", "x", "v1", "v1.1.2.3", "v2.1.abcdefghijklmnop.sig", "v1..abcdefghijklmnop.sig",
        "v1.notanumber.abcdefghijklmnop.AAAA", "v1.1700000000000.short.AAAA",
        "v1.1700000000000.abcdefghijklmnop.!!!notbase64!!!",
        "v1.1700000000000.abcdefghijklmnop." + "A" * 86,
        "v1.1700000000000.abcdefghijklmnop.AAAA.extra", "a" * 5000,
    ])
    def test_malformed_proofs_are_rejected_not_crashed_on(self, client, live_session, garbage):
        resp = self._get(client, garbage)
        assert resp.status_code == 401
        assert resp.get_json()["error"]["code"] == "UNAUTHORIZED"

    # --- sessions that cannot be honoured ------------------------------------------

    def test_session_created_before_device_binding_is_never_honoured(self, client):
        legacy = _session_row(device_key=None)
        with patch("middleware.require_session.fetch_one", return_value=legacy):
            proof = sign_proof(OWNER_PRIVATE, TEST_TOKEN, "GET", self.URL)
            assert self._get(client, proof).status_code == 401

    def test_legacy_cache_entry_that_is_just_a_user_id_is_ignored(self, client, redis_conn):
        import json
        redis_conn.setex(f"session_{get_test_token_hash()}", 120, json.dumps(TEST_U_ID))
        with patch("middleware.require_session.fetch_one", return_value=None):
            proof = sign_proof(OWNER_PRIVATE, TEST_TOKEN, "GET", self.URL)
            assert self._get(client, proof).status_code == 401

    def test_unknown_or_expired_token_is_rejected(self, client):
        with patch("middleware.require_session.fetch_one", return_value=None):
            proof = sign_proof(OWNER_PRIVATE, TEST_TOKEN, "GET", self.URL)
            assert self._get(client, proof).status_code == 401

    def test_missing_bearer_prefix_is_rejected(self, client, live_session):
        h = _headers(sign_proof(OWNER_PRIVATE, TEST_TOKEN, "GET", self.URL))
        h["Authorization"] = TEST_TOKEN
        assert client.get(self.URL, headers=h).status_code == 401

    # --- who may present a session -----------------------------------------------------

    def test_without_the_client_key_a_perfect_session_is_still_refused(self, client, live_session):
        proof = sign_proof(OWNER_PRIVATE, TEST_TOKEN, "GET", self.URL)
        assert self._get(client, proof, key=None).status_code == 401

    def test_the_bot_key_does_not_open_session_routes(self, client, live_session):
        from conftest import TEST_API_KEY
        proof = sign_proof(OWNER_PRIVATE, TEST_TOKEN, "GET", self.URL)
        h = _headers(proof, key=None)
        h["X-API-KEY"] = TEST_API_KEY
        assert client.get(self.URL, headers=h).status_code == 401

    # --- the second factor: browser / OS family ------------------------------------------

    def test_a_different_browser_ends_the_session(self, client, live_session):
        proof = sign_proof(OWNER_PRIVATE, TEST_TOKEN, "GET", self.URL)
        with patch("middleware.require_session.execute") as delete:
            resp = self._get(client, proof, ua=FIREFOX_WIN)
        assert resp.status_code == 401
        assert "DELETE FROM sessions" in delete.call_args[0][0]
        assert delete.call_args[0][1] == (get_test_token_hash(),)

    def test_the_ended_session_is_dropped_from_the_cache_too(self, client, live_session, redis_conn):
        self._get(client, sign_proof(OWNER_PRIVATE, TEST_TOKEN, "GET", self.URL))
        assert redis_conn.exists(f"session_{get_test_token_hash()}")
        with patch("middleware.require_session.execute"):
            self._get(client, sign_proof(OWNER_PRIVATE, TEST_TOKEN, "GET", self.URL), ua=FIREFOX_WIN)
        assert not redis_conn.exists(f"session_{get_test_token_hash()}")

    def test_a_thief_cannot_log_the_victim_out_by_sending_a_strange_user_agent(self, client, live_session):
        """Revocation happens only after the signature proved the caller holds the key."""
        with patch("middleware.require_session.execute") as delete:
            resp = self._get(client, None, ua=FIREFOX_WIN)
            forged = sign_proof(THIEF_PRIVATE, TEST_TOKEN, "GET", self.URL)
            resp2 = self._get(client, forged, ua=FIREFOX_WIN)
        assert resp.status_code == resp2.status_code == 401
        delete.assert_not_called()

    # --- degraded and failing dependencies ------------------------------------------------------

    def test_redis_down_for_the_nonce_check_degrades_but_does_not_break_login(self, client, live_session, caplog):
        import logging
        proof = sign_proof(OWNER_PRIVATE, TEST_TOKEN, "GET", self.URL)
        with caplog.at_level(logging.ERROR), \
             patch("middleware.require_session.claim_once", return_value=None):
            resp = self._get(client, proof)
        assert resp.status_code == 200
        assert "nonce check skipped" in caplog.text

    def test_redis_down_does_not_let_a_bad_signature_through(self, client, live_session):
        forged = sign_proof(THIEF_PRIVATE, TEST_TOKEN, "GET", self.URL)
        with patch("middleware.require_session.claim_once", return_value=None):
            assert self._get(client, forged).status_code == 401

    def test_database_failure_returns_generic_500_not_the_session(self, client):
        with patch("middleware.require_session.fetch_one",
                   side_effect=RuntimeError("dsn=postgres://u:hunter2@db")):
            proof = sign_proof(OWNER_PRIVATE, TEST_TOKEN, "GET", self.URL)
            resp = self._get(client, proof)
        assert resp.status_code == 500
        assert "hunter2" not in resp.get_data(as_text=True)

    def test_rejection_reason_is_logged_not_returned(self, client, live_session, caplog):
        import logging
        with caplog.at_level(logging.WARNING):
            resp = self._get(client, None)
        assert "proof missing" in caplog.text
        assert "proof" not in resp.get_data(as_text=True).lower()


class TestViewerOnPublicRoutes:
    """get_viewer(): a bad credential on a public route means 'anonymous', never an error."""
    URL = f"/api/users/{TEST_U_ID}/dashboard"

    def _get(self, client, proof, **kw):
        return client.get(self.URL, headers=_headers(proof, **kw))

    def _db(self):
        return patch("api.dashboard.fetch_one", return_value=FAKE_USER)

    def test_the_owner_with_a_valid_proof_sees_the_full_profile(self, client, live_session):
        proof = sign_proof(OWNER_PRIVATE, TEST_TOKEN, "GET", self.URL)
        with self._db(), patch("api.dashboard.fetch_all", side_effect=[[], [], []]):
            data = self._get(client, proof).get_json()["data"]
        assert "restricted" not in data
        assert data["user"]["u_phone"] == FAKE_USER["u_phone"]

    def test_a_stolen_token_without_the_key_only_ever_sees_a_name(self, client, live_session):
        with self._db(), patch("api.dashboard.fetch_all") as catalogue:
            resp = self._get(client, None)
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["restricted"] is True
        assert data["user"] == {"u_id": TEST_U_ID, "u_name": FAKE_USER["u_name"]}
        catalogue.assert_not_called()

    def test_a_forged_proof_is_treated_as_anonymous(self, client, live_session):
        forged = sign_proof(THIEF_PRIVATE, TEST_TOKEN, "GET", self.URL)
        with self._db(), patch("api.dashboard.fetch_all"):
            data = self._get(client, forged).get_json()["data"]
        assert data["restricted"] is True

    def test_a_garbage_token_is_treated_as_anonymous(self, client):
        with patch("middleware.require_session.fetch_one", return_value=None), \
             self._db(), patch("api.dashboard.fetch_all"):
            resp = self._get(client, "v1.1.2.3", token="garbage")
        assert resp.status_code == 200
        assert resp.get_json()["data"]["restricted"] is True

    def test_no_credentials_at_all_is_anonymous(self, client):
        with self._db(), patch("api.dashboard.fetch_all"):
            resp = client.get(self.URL, headers={"X-Client-Key": TEST_WEB_KEY})
        assert resp.get_json()["data"]["restricted"] is True

    def test_the_bot_key_is_never_a_viewer(self, client):
        from conftest import TEST_API_KEY
        with self._db(), patch("api.dashboard.fetch_all"):
            resp = client.get(self.URL, headers={"X-API-KEY": TEST_API_KEY})
        assert resp.get_json()["data"]["restricted"] is True


class TestLogoutEndsTheSession:
    def test_the_token_stops_working_after_logout(self, client, live_session):
        proof = sign_proof(OWNER_PRIVATE, TEST_TOKEN, "POST", "/api/logout")
        with patch("middleware.require_session.execute") as delete:
            resp = client.post("/api/logout", headers=_headers(proof))
        assert resp.status_code == 200
        assert "DELETE FROM sessions" in delete.call_args[0][0]

        # The row is gone and the cache entry was dropped: the next request
        # misses the cache, finds nothing in Postgres, and is refused.
        with patch("middleware.require_session.fetch_one", return_value=None):
            again = sign_proof(OWNER_PRIVATE, TEST_TOKEN, "GET", "/api/me")
            assert client.get("/api/me", headers=_headers(again)).status_code == 401
