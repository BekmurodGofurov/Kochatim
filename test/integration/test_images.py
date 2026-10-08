"""
Integration tests — api/images.py

POST /api/img, POST /api/img/upload, GET /api/img/by-type,
GET /api/img/<file_id> (Telegram proksi).
"""
import io
from unittest.mock import MagicMock, patch

import pytest
import requests

from conftest import TEST_API_KEY, TEST_TOKEN

API_H = {"X-API-KEY": TEST_API_KEY, "Content-Type": "application/json"}
SESSION_H = {"Authorization": f"Bearer {TEST_TOKEN}"}


# ─── POST /api/img ────────────────────────────────────────────────────────────

class TestAddImg:
    URL = "/api/img"

    def test_insert_when_no_existing_row(self, client):
        with patch("api.images.process_image_input", return_value="https://i.ibb.co/a.png"), \
             patch("api.images.fetch_one", return_value=None), \
             patch("api.images.execute") as mock_exec:
            resp = client.post(self.URL, json={"t_id": 10, "i_url": "https://i.ibb.co/a.png"},
                               headers=API_H)
        assert resp.status_code == 200
        assert resp.get_json()["data"] == {"saved": True}
        assert "INSERT INTO img" in mock_exec.call_args[0][0]

    def test_update_when_row_exists(self, client):
        with patch("api.images.process_image_input", return_value="https://i.ibb.co/b.png"), \
             patch("api.images.fetch_one", return_value={"i_id": 3}), \
             patch("api.images.execute") as mock_exec:
            resp = client.post(self.URL, json={"t_id": 10, "i_url": "https://i.ibb.co/b.png"},
                               headers=API_H)
        assert resp.status_code == 200
        assert "UPDATE img" in mock_exec.call_args[0][0]

    def test_telegram_file_id_is_converted_before_save(self, client):
        with patch("api.images.process_image_input",
                   return_value="https://i.ibb.co/c.png") as mock_proc, \
             patch("api.images.fetch_one", return_value=None), \
             patch("api.images.execute") as mock_exec:
            client.post(self.URL, json={"t_id": 10, "i_url": "AgACAgIAAxk"}, headers=API_H)
        mock_proc.assert_called_once_with("AgACAgIAAxk")
        assert "https://i.ibb.co/c.png" in mock_exec.call_args[0][1]

    def test_missing_t_id_returns_400(self, client):
        resp = client.post(self.URL, json={"i_url": "https://x/a.png"}, headers=API_H)
        assert resp.status_code == 400

    def test_missing_i_url_returns_400(self, client):
        resp = client.post(self.URL, json={"t_id": 10}, headers=API_H)
        assert resp.status_code == 400

    def test_empty_body_returns_400(self, client):
        resp = client.post(self.URL, json={}, headers=API_H)
        assert resp.status_code == 400

    def test_non_integer_t_id_returns_400(self, client):
        with patch("api.images.process_image_input", return_value="https://x/a.png"):
            resp = client.post(self.URL, json={"t_id": "abc", "i_url": "https://x/a.png"},
                               headers=API_H)
        assert resp.status_code == 400
        assert "integer" in resp.get_json()["error"]["message"]

    def test_requires_api_key(self, client):
        resp = client.post(self.URL, json={"t_id": 10, "i_url": "https://x/a.png"},
                           headers={"Content-Type": "application/json"})
        assert resp.status_code == 401

    def test_wrong_api_key_returns_401(self, client):
        resp = client.post(self.URL, json={"t_id": 10, "i_url": "https://x/a.png"},
                           headers={"X-API-KEY": "nope", "Content-Type": "application/json"})
        assert resp.status_code == 401

    def test_db_failure_returns_500(self, client):
        with patch("api.images.process_image_input", return_value="https://x/a.png"), \
             patch("api.images.fetch_one", side_effect=Exception("db down")):
            resp = client.post(self.URL, json={"t_id": 10, "i_url": "https://x/a.png"},
                               headers=API_H)
        assert resp.status_code == 500
        assert resp.get_json()["ok"] is False


# ─── POST /api/img/upload ─────────────────────────────────────────────────────

class TestUploadImgDirect:
    URL = "/api/img/upload"

    def test_success_returns_url(self, client, mock_session):
        with patch("utils.images_v2.upload_to_imgbb", return_value="https://i.ibb.co/d.png"):
            resp = client.post(
                self.URL,
                data={"image": (io.BytesIO(b"fake-png-bytes"), "photo.png")},
                headers=SESSION_H,
                content_type="multipart/form-data",
            )
        assert resp.status_code == 200
        assert resp.get_json()["data"] == {"url": "https://i.ibb.co/d.png"}

    def test_file_bytes_are_forwarded(self, client, mock_session):
        with patch("utils.images_v2.upload_to_imgbb",
                   return_value="https://i.ibb.co/d.png") as mock_up:
            client.post(
                self.URL,
                data={"image": (io.BytesIO(b"abc123"), "photo.png")},
                headers=SESSION_H,
                content_type="multipart/form-data",
            )
        assert mock_up.call_args[0][0] == b"abc123"

    def test_missing_file_field_returns_400(self, client, mock_session):
        resp = client.post(self.URL, data={}, headers=SESSION_H,
                           content_type="multipart/form-data")
        assert resp.status_code == 400
        assert "No image file" in resp.get_json()["error"]["message"]

    def test_empty_filename_returns_400(self, client, mock_session):
        resp = client.post(
            self.URL,
            data={"image": (io.BytesIO(b""), "")},
            headers=SESSION_H,
            content_type="multipart/form-data",
        )
        assert resp.status_code == 400

    def test_imgbb_failure_returns_500(self, client, mock_session):
        with patch("utils.images_v2.upload_to_imgbb", return_value=None):
            resp = client.post(
                self.URL,
                data={"image": (io.BytesIO(b"x"), "photo.png")},
                headers=SESSION_H,
                content_type="multipart/form-data",
            )
        assert resp.status_code == 500
        assert "ImgBB" in resp.get_json()["error"]["message"]

    def test_requires_session(self, client):
        resp = client.post(
            self.URL,
            data={"image": (io.BytesIO(b"x"), "photo.png")},
            content_type="multipart/form-data",
        )
        assert resp.status_code == 401

    def test_api_key_does_not_grant_access(self, client):
        """Bu endpoint sessiya talab qiladi — bot kaliti yetarli emas."""
        resp = client.post(
            self.URL,
            data={"image": (io.BytesIO(b"x"), "photo.png")},
            headers={"X-API-KEY": TEST_API_KEY},
            content_type="multipart/form-data",
        )
        assert resp.status_code == 401


# ─── GET /api/img/by-type ─────────────────────────────────────────────────────

class TestGetImgByType:
    URL = "/api/img/by-type"

    def test_returns_url_when_found(self, client):
        with patch("api.images.fetch_one", return_value={"i_url": "https://i.ibb.co/e.png"}):
            resp = client.get(f"{self.URL}?t_id=10", headers=API_H)
        assert resp.status_code == 200
        assert resp.get_json()["data"] == "https://i.ibb.co/e.png"

    def test_returns_null_when_not_found(self, client):
        with patch("api.images.fetch_one", return_value=None):
            resp = client.get(f"{self.URL}?t_id=999", headers=API_H)
        assert resp.status_code == 200
        assert resp.get_json()["data"] is None

    def test_missing_t_id_returns_400(self, client):
        resp = client.get(self.URL, headers=API_H)
        assert resp.status_code == 400

    def test_non_integer_t_id_returns_400(self, client):
        resp = client.get(f"{self.URL}?t_id=abc", headers=API_H)
        assert resp.status_code == 400
        assert "integer" in resp.get_json()["error"]["message"]

    def test_requires_api_key(self, client):
        resp = client.get(f"{self.URL}?t_id=10")
        assert resp.status_code == 401

    def test_db_failure_returns_500(self, client):
        with patch("api.images.fetch_one", side_effect=Exception("db down")):
            resp = client.get(f"{self.URL}?t_id=10", headers=API_H)
        assert resp.status_code == 500


# ─── GET /api/img/<file_id> — Telegram proksi ────────────────────────────────

def _tg_get_file(file_path="photos/f.jpg", ok=True, status=200):
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = {"ok": ok, "result": {"file_path": file_path} if file_path else {}}
    return resp


def _tg_binary(content=b"\x89PNG", status=200, content_type="image/png"):
    resp = MagicMock()
    resp.status_code = status
    resp.content = content
    resp.headers = {"Content-Type": content_type}
    return resp


class TestProxyTelegramImage:
    URL = "/api/img/AgACAgIAAxk"

    def test_success_returns_image_bytes(self, client):
        with patch("api.images.requests.get",
                   side_effect=[_tg_get_file(), _tg_binary(b"\x89PNGdata")]):
            resp = client.get(self.URL)
        assert resp.status_code == 200
        assert resp.data == b"\x89PNGdata"

    def test_passes_through_content_type(self, client):
        with patch("api.images.requests.get",
                   side_effect=[_tg_get_file(), _tg_binary(content_type="image/jpeg")]):
            resp = client.get(self.URL)
        assert resp.headers["Content-Type"] == "image/jpeg"

    def test_defaults_content_type_to_jpeg(self, client):
        binary = _tg_binary()
        binary.headers = {}
        with patch("api.images.requests.get", side_effect=[_tg_get_file(), binary]):
            resp = client.get(self.URL)
        assert resp.headers["Content-Type"] == "image/jpeg"

    def test_sets_cache_header(self, client):
        with patch("api.images.requests.get", side_effect=[_tg_get_file(), _tg_binary()]):
            resp = client.get(self.URL)
        assert "max-age=86400" in resp.headers["Cache-Control"]

    def test_needs_no_auth(self, client):
        """Frontend <img src> orqali chaqiradi — header yubora olmaydi."""
        with patch("api.images.requests.get", side_effect=[_tg_get_file(), _tg_binary()]):
            resp = client.get(self.URL)
        assert resp.status_code == 200

    def test_missing_bot_token_returns_500(self, client):
        with patch("api.images.Config.BOT_TOKEN", ""):
            resp = client.get(self.URL)
        assert resp.status_code == 500

    def test_get_file_http_error_returns_502(self, client):
        with patch("api.images.requests.get", return_value=_tg_get_file(status=500)):
            resp = client.get(self.URL)
        assert resp.status_code == 502

    def test_invalid_file_id_returns_404(self, client):
        with patch("api.images.requests.get", return_value=_tg_get_file(ok=False)):
            resp = client.get(self.URL)
        assert resp.status_code == 404

    def test_missing_file_path_returns_404(self, client):
        with patch("api.images.requests.get", return_value=_tg_get_file(file_path=None)):
            resp = client.get(self.URL)
        assert resp.status_code == 404

    def test_binary_fetch_failure_returns_502(self, client):
        with patch("api.images.requests.get",
                   side_effect=[_tg_get_file(), _tg_binary(status=404)]):
            resp = client.get(self.URL)
        assert resp.status_code == 502

    def test_network_error_returns_500(self, client):
        """requests xatosi ushlanmagan — global errorhandler 500 beradi."""
        with patch("api.images.requests.get", side_effect=requests.ConnectionError("down")):
            resp = client.get(self.URL)
        assert resp.status_code == 500

    def test_bot_token_is_not_leaked_in_response(self, client):
        with patch("api.images.requests.get", side_effect=[_tg_get_file(), _tg_binary()]):
            resp = client.get(self.URL)
        assert b"TEST_BOT_TOKEN" not in resp.data
