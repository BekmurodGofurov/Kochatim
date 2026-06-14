"""
Integration tests — api/partners.py
Hamkorlik tizimi endpointlari.
"""
from datetime import datetime
from unittest.mock import patch, MagicMock

import pytest

from conftest import (
    TEST_API_KEY, TEST_TOKEN, TEST_U_ID,
    FAKE_PARTNER, FAKE_INVITE, NOW,
)

API_H = {"X-API-KEY": TEST_API_KEY, "Content-Type": "application/json"}
SESSION_H = {"Authorization": f"Bearer {TEST_TOKEN}", "Content-Type": "application/json"}

PARTNER_U_ID = 987654321


# ─── GET /api/partners (session) ──────────────────────────────────────────────

class TestListPartnersMe:
    URL = "/api/partners"

    def test_success_returns_list(self, client, mock_session):
        with patch("api.partners.get_cache", return_value=None), \
             patch("api.partners.fetch_all", return_value=[FAKE_PARTNER]), \
             patch("api.partners.set_cache"):
            resp = client.get(self.URL, headers=SESSION_H)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True
        assert isinstance(data["data"], list)
        assert data["data"][0]["u_id"] == PARTNER_U_ID

    def test_cached_result_returned(self, client, mock_session):
        with patch("api.partners.get_cache", return_value=[FAKE_PARTNER]):
            resp = client.get(self.URL, headers=SESSION_H)
        assert resp.status_code == 200
        assert len(resp.get_json()["data"]) == 1

    def test_empty_partners(self, client, mock_session):
        with patch("api.partners.get_cache", return_value=None), \
             patch("api.partners.fetch_all", return_value=[]), \
             patch("api.partners.set_cache"):
            resp = client.get(self.URL, headers=SESSION_H)
        assert resp.get_json()["data"] == []

    def test_no_auth_returns_401(self, client):
        resp = client.get(self.URL)
        assert resp.status_code == 401


# ─── POST /api/partners/remove (session) ──────────────────────────────────────

class TestRemovePartner:
    URL = "/api/partners/remove"

    def test_success(self, client, mock_session):
        remover = {"u_name": "Test Foydalanuvchi"}
        with patch("api.partners.execute"), \
             patch("api.partners.fetch_one", return_value=remover), \
             patch("api.partners._invalidate_partners"), \
             patch("api.partners.send_message"):
            resp = client.post(
                self.URL, json={"p_id": PARTNER_U_ID}, headers=SESSION_H
            )
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["removed"] is True
        assert data["p_id"] == PARTNER_U_ID

    def test_notification_sent(self, client, mock_session):
        with patch("api.partners.execute"), \
             patch("api.partners.fetch_one", return_value={"u_name": "Ali"}), \
             patch("api.partners._invalidate_partners"), \
             patch("api.partners.send_message") as mock_msg:
            resp = client.post(
                self.URL, json={"p_id": PARTNER_U_ID}, headers=SESSION_H
            )
        assert resp.status_code == 200
        mock_msg.assert_called_once()
        call_args = mock_msg.call_args[0]
        assert call_args[0] == PARTNER_U_ID
        assert isinstance(call_args[1], str) and len(call_args[1]) > 0

    def test_missing_p_id_returns_400(self, client, mock_session):
        resp = client.post(self.URL, json={}, headers=SESSION_H)
        assert resp.status_code == 400

    def test_string_p_id_returns_400(self, client, mock_session):
        resp = client.post(self.URL, json={"p_id": "abc"}, headers=SESSION_H)
        assert resp.status_code == 400

    def test_no_auth_returns_401(self, client):
        resp = client.post(self.URL, json={"p_id": PARTNER_U_ID})
        assert resp.status_code == 401


# ─── GET /api/partners/invite-token (session) ─────────────────────────────────

class TestGetInviteToken:
    URL = "/api/partners/invite-token"

    def test_success_existing_token(self, client, mock_session):
        invite = {"token": "existing-token-abc"}
        payload = {"token": "existing-token-abc", "bot_username": "test_kochatim_bot"}
        with patch("api.partners.get_cache", return_value=None), \
             patch("api.partners.fetch_one", return_value=invite), \
             patch("api.partners.set_cache"):
            resp = client.get(self.URL, headers=SESSION_H)
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert "token" in data
        assert "bot_username" in data

    def test_creates_new_token_when_none(self, client, mock_session):
        with patch("api.partners.get_cache", return_value=None), \
             patch("api.partners.fetch_one", return_value=None), \
             patch("api.partners.execute"), \
             patch("api.partners.set_cache"):
            resp = client.get(self.URL, headers=SESSION_H)
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert "token" in data
        assert len(data["token"]) > 5

    def test_cached_result(self, client, mock_session):
        cached = {"token": "cached-token", "bot_username": "bot"}
        with patch("api.partners.get_cache", return_value=cached):
            resp = client.get(self.URL, headers=SESSION_H)
        assert resp.get_json()["data"]["token"] == "cached-token"

    def test_no_auth_returns_401(self, client):
        resp = client.get(self.URL)
        assert resp.status_code == 401


# ─── GET /api/users/<u_id>/partners (API key) ─────────────────────────────────

class TestGetUserPartners:
    def test_success(self, client):
        rows = [{"u_id": PARTNER_U_ID, "u_name": "Hamkor", "u_username": "hamkor"}]
        with patch("api.partners.fetch_all", return_value=rows):
            resp = client.get(f"/api/users/{TEST_U_ID}/partners", headers=API_H)
        assert resp.status_code == 200
        assert resp.get_json()["data"][0]["u_id"] == PARTNER_U_ID

    def test_empty_list(self, client):
        with patch("api.partners.fetch_all", return_value=[]):
            resp = client.get(f"/api/users/{TEST_U_ID}/partners", headers=API_H)
        assert resp.get_json()["data"] == []

    def test_no_api_key_returns_401(self, client):
        resp = client.get(f"/api/users/{TEST_U_ID}/partners")
        assert resp.status_code == 401


# ─── POST /api/partners/accept (API key) ─────────────────────────────────────

class TestAcceptPartnerInvite:
    URL = "/api/partners/accept"

    def _valid_invite(self):
        return {
            "inviter_u_id": PARTNER_U_ID,
            "expires_at": datetime(2099, 1, 1),
            "used_at": None,
        }

    def test_success_new_partnership(self, client):
        with patch("api.partners.fetch_one", side_effect=[
            self._valid_invite(),         # invite lookup
            {"u_id": PARTNER_U_ID},       # inviter user
            {"u_id": TEST_U_ID},          # invitee user
            None,                          # partner check (not exists)
        ]), \
        patch("api.partners.execute"), \
        patch("api.partners._invalidate_partners"), \
        patch("api.partners.invalidate_cache"):
            resp = client.post(self.URL, json={
                "token": "valid-token", "u_id": TEST_U_ID,
            }, headers=API_H)
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["accepted"] is True
        assert data["already_partners"] is False

    def test_already_partners(self, client):
        with patch("api.partners.fetch_one", side_effect=[
            self._valid_invite(),
            {"u_id": PARTNER_U_ID},
            {"u_id": TEST_U_ID},
            {"u_id": PARTNER_U_ID},   # partner already exists
        ]):
            resp = client.post(self.URL, json={
                "token": "valid-token", "u_id": TEST_U_ID,
            }, headers=API_H)
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["accepted"] is False
        assert data["already_partners"] is True

    def test_invalid_token_returns_400(self, client):
        with patch("api.partners.fetch_one", return_value=None):
            resp = client.post(self.URL, json={
                "token": "invalid", "u_id": TEST_U_ID,
            }, headers=API_H)
        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "INVALID_TOKEN"

    def test_expired_invite_returns_400(self, client):
        expired = {
            "inviter_u_id": PARTNER_U_ID,
            "expires_at": datetime(2000, 1, 1),
            "used_at": None,
        }
        with patch("api.partners.fetch_one", return_value=expired):
            resp = client.post(self.URL, json={
                "token": "expired-token", "u_id": TEST_U_ID,
            }, headers=API_H)
        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "INVITE_EXPIRED"

    def test_used_invite_returns_400(self, client):
        used = {
            "inviter_u_id": PARTNER_U_ID,
            "expires_at": datetime(2099, 1, 1),
            "used_at": datetime(2026, 1, 1),
        }
        with patch("api.partners.fetch_one", return_value=used):
            resp = client.post(self.URL, json={
                "token": "used-token", "u_id": TEST_U_ID,
            }, headers=API_H)
        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "INVITE_USED"

    def test_self_invite_returns_400(self, client):
        invite = {
            "inviter_u_id": TEST_U_ID,
            "expires_at": datetime(2099, 1, 1),
            "used_at": None,
        }
        with patch("api.partners.fetch_one", return_value=invite):
            resp = client.post(self.URL, json={
                "token": "self-token", "u_id": TEST_U_ID,
            }, headers=API_H)
        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "SELF"

    def test_missing_token_returns_400(self, client):
        resp = client.post(self.URL, json={"u_id": TEST_U_ID}, headers=API_H)
        assert resp.status_code == 400

    def test_missing_u_id_returns_400(self, client):
        resp = client.post(self.URL, json={"token": "tok"}, headers=API_H)
        assert resp.status_code == 400

    def test_no_api_key_returns_401(self, client):
        resp = client.post(self.URL, json={"token": "tok", "u_id": TEST_U_ID})
        assert resp.status_code == 401


# ─── POST /api/partners/decline (API key) ────────────────────────────────────

class TestDeclinePartnerInvite:
    URL = "/api/partners/decline"

    def test_success(self, client):
        invite = {"inviter_u_id": PARTNER_U_ID}
        with patch("api.partners.fetch_one", return_value=invite):
            resp = client.post(self.URL, json={
                "token": "some-token", "u_id": TEST_U_ID,
            }, headers=API_H)
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["declined"] is True
        assert data["inviter_u_id"] == PARTNER_U_ID
        assert data["invitee_u_id"] == TEST_U_ID

    def test_invalid_token_returns_400(self, client):
        with patch("api.partners.fetch_one", return_value=None):
            resp = client.post(self.URL, json={
                "token": "invalid", "u_id": TEST_U_ID,
            }, headers=API_H)
        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "INVALID_TOKEN"

    def test_missing_token_returns_400(self, client):
        resp = client.post(self.URL, json={"u_id": TEST_U_ID}, headers=API_H)
        assert resp.status_code == 400

    def test_no_api_key_returns_401(self, client):
        resp = client.post(self.URL, json={"token": "t", "u_id": TEST_U_ID})
        assert resp.status_code == 401
