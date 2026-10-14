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
from conftest import SESSION_HEADERS, WEB_HEADERS, TEST_WEB_KEY

API_H = {"X-API-KEY": TEST_API_KEY, "Content-Type": "application/json"}
SESSION_H = {k: v for k, v in SESSION_HEADERS.items() if k != "Content-Type"}


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


@pytest.fixture
def known_file_id():
    """The id is one the app stored (a user photo or a variety image)."""
    with patch("api.images.fetch_one", return_value={"known": 1}) as lookup:
        yield lookup


class TestProxyTelegramImage:
    URL = "/api/img/AgACAgIAAxk"

    def _get(self, client, url=None, headers=WEB_HEADERS):
        return client.get(url or self.URL, headers=headers)

    # --- happy path --------------------------------------------------------------

    def test_success_returns_image_bytes(self, client, known_file_id):
        with patch("api.images.requests.get",
                   side_effect=[_tg_get_file(), _tg_binary(b"\x89PNGdata")]):
            resp = self._get(client)
        assert resp.status_code == 200
        assert resp.data == b"\x89PNGdata"

    def test_passes_through_content_type(self, client, known_file_id):
        with patch("api.images.requests.get",
                   side_effect=[_tg_get_file(), _tg_binary(content_type="image/jpeg")]):
            resp = self._get(client)
        assert resp.headers["Content-Type"] == "image/jpeg"

    def test_defaults_content_type_to_jpeg(self, client, known_file_id):
        binary = _tg_binary()
        binary.headers = {}
        with patch("api.images.requests.get", side_effect=[_tg_get_file(), binary]):
            resp = self._get(client)
        assert resp.headers["Content-Type"] == "image/jpeg"

    def test_sets_cache_header(self, client, known_file_id):
        with patch("api.images.requests.get", side_effect=[_tg_get_file(), _tg_binary()]):
            resp = self._get(client)
        assert "max-age=86400" in resp.headers["Cache-Control"]

    def test_is_served_with_nosniff_and_a_locked_down_csp(self, client, known_file_id):
        with patch("api.images.requests.get", side_effect=[_tg_get_file(), _tg_binary()]):
            resp = self._get(client)
        assert resp.headers["X-Content-Type-Options"] == "nosniff"
        assert "sandbox" in resp.headers["Content-Security-Policy"]

    def test_accepts_key_in_query_for_img_tags(self, client, known_file_id):
        """<img src> cannot set headers, so this route also takes ?k=<web key>."""
        with patch("api.images.requests.get", side_effect=[_tg_get_file(), _tg_binary()]):
            resp = client.get(f"{self.URL}?k={TEST_WEB_KEY}")
        assert resp.status_code == 200

    def test_without_the_client_key_telegram_is_never_contacted(self, client, known_file_id):
        with patch("api.images.requests.get") as tg:
            resp = client.get(self.URL)
        assert resp.status_code == 401
        tg.assert_not_called()

    # --- only ids the app stored ---------------------------------------------------

    def test_an_id_nobody_stored_never_reaches_telegram(self, client):
        with patch("api.images.fetch_one", return_value=None), \
             patch("api.images.requests.get") as tg:
            resp = self._get(client, "/api/img/AgACAgIA_made_up_id")
        assert resp.status_code == 404
        tg.assert_not_called()

    def test_lookup_checks_user_photos_and_variety_images_with_bound_params(self, client):
        with patch("api.images.fetch_one", return_value=None) as lookup:
            self._get(client, "/api/img/x%27%20OR%201=1--")
        sql, params = lookup.call_args[0]
        assert "u_photo" in sql and "img" in sql and "i_url" in sql
        assert params == ("x' OR 1=1--", "x' OR 1=1--")
        assert "OR 1=1" not in sql

    def test_a_known_id_is_remembered_so_the_database_is_not_asked_again(self, client, known_file_id):
        with patch("api.images.requests.get",
                   side_effect=[_tg_get_file(), _tg_binary(), _tg_get_file(), _tg_binary()]):
            self._get(client)
            self._get(client)
        assert known_file_id.call_count == 1

    def test_an_unknown_id_is_not_cached_as_known(self, client):
        with patch("api.images.fetch_one", side_effect=[None, {"known": 1}]) as lookup, \
             patch("api.images.requests.get", side_effect=[_tg_get_file(), _tg_binary()]):
            assert self._get(client).status_code == 404
            assert self._get(client).status_code == 200  # it became known (e.g. a new upload)
        assert lookup.call_count == 2

    def test_database_failure_returns_generic_500(self, client):
        with patch("api.images.fetch_one", side_effect=RuntimeError("dsn=postgres://u:hunter2@db")):
            resp = self._get(client)
        assert resp.status_code == 500
        assert "hunter2" not in resp.get_data(as_text=True)

    # --- request budget ---------------------------------------------------------------

    def test_an_ip_that_floods_the_route_is_throttled(self, client, known_file_id):
        with patch("api.images._IMG_RATE_LIMIT", 3), \
             patch("api.images.requests.get", side_effect=lambda *a, **k: _tg_get_file()) as tg:
            codes = [client.get(self.URL, headers={**WEB_HEADERS, "X-Real-IP": "198.51.100.5"}).status_code
                     for _ in range(6)]
        assert codes[3:] == [429, 429, 429]
        assert tg.call_count <= 6  # throttled requests made no Telegram call

    def test_throttled_requests_never_touch_telegram_or_the_database(self, client, known_file_id):
        headers = {**WEB_HEADERS, "X-Real-IP": "198.51.100.5"}
        with patch("api.images._IMG_RATE_LIMIT", 1), \
             patch("api.images.requests.get", side_effect=[_tg_get_file(), _tg_binary()]) as tg:
            client.get(self.URL, headers=headers)
            before = (tg.call_count, known_file_id.call_count)
            resp = client.get(self.URL, headers=headers)
        assert resp.status_code == 429
        assert int(resp.headers["Retry-After"]) > 0
        assert (tg.call_count, known_file_id.call_count) == before

    def test_the_budget_is_per_ip(self, client, known_file_id):
        with patch("api.images._IMG_RATE_LIMIT", 1), \
             patch("api.images.requests.get", side_effect=lambda *a, **k: _tg_get_file()):
            client.get(self.URL, headers={**WEB_HEADERS, "X-Real-IP": "198.51.100.5"})
            other = client.get(self.URL, headers={**WEB_HEADERS, "X-Real-IP": "198.51.100.6"})
        assert other.status_code != 429

    def test_spoofed_forwarded_for_does_not_buy_a_fresh_budget(self, client, known_file_id):
        with patch("api.images._IMG_RATE_LIMIT", 1), \
             patch("api.images.requests.get", side_effect=lambda *a, **k: _tg_get_file()):
            for i in range(2):
                resp = client.get(self.URL, headers={**WEB_HEADERS, "X-Real-IP": "198.51.100.5",
                                                     "X-Forwarded-For": f"10.0.0.{i}"})
        assert resp.status_code == 429

    def test_redis_outage_does_not_take_images_down(self, client, known_file_id):
        with patch("api.images.ratelimit.record", return_value=None), \
             patch("api.images.requests.get", side_effect=[_tg_get_file(), _tg_binary()]):
            assert self._get(client).status_code == 200

    # --- Telegram failures ----------------------------------------------------------------

    def test_missing_bot_token_returns_500(self, client, known_file_id):
        with patch("api.images.Config.BOT_TOKEN", ""):
            resp = self._get(client)
        assert resp.status_code == 500

    def test_get_file_http_error_returns_502(self, client, known_file_id):
        with patch("api.images.requests.get", return_value=_tg_get_file(status=500)):
            resp = self._get(client)
        assert resp.status_code == 502

    def test_invalid_file_id_returns_404(self, client, known_file_id):
        with patch("api.images.requests.get", return_value=_tg_get_file(ok=False)):
            resp = self._get(client)
        assert resp.status_code == 404

    def test_missing_file_path_returns_404(self, client, known_file_id):
        with patch("api.images.requests.get", return_value=_tg_get_file(file_path=None)):
            resp = self._get(client)
        assert resp.status_code == 404

    def test_binary_fetch_failure_returns_502(self, client, known_file_id):
        with patch("api.images.requests.get",
                   side_effect=[_tg_get_file(), _tg_binary(status=404)]):
            resp = self._get(client)
        assert resp.status_code == 502

    def test_every_telegram_call_has_a_timeout(self, client, known_file_id):
        with patch("api.images.requests.get", side_effect=[_tg_get_file(), _tg_binary()]) as tg:
            self._get(client)
        assert all(c.kwargs.get("timeout") for c in tg.call_args_list)

    def test_the_file_id_travels_as_a_parameter_not_in_the_url(self, client):
        weird = "x?bot=evil&file_id=other"   # '/' cannot reach the route at all (404); '?' and '&' can
        with patch("api.images.fetch_one", return_value={"known": 1}), \
             patch("api.images.requests.get", side_effect=[_tg_get_file(), _tg_binary()]) as tg:
            client.get("/api/img/" + "x%3Fbot%3Devil%26file_id%3Dother", headers=WEB_HEADERS)
        first = tg.call_args_list[0]
        assert first.kwargs["params"] == {"file_id": weird}
        assert first.args[0].endswith("/getFile")

    @pytest.mark.parametrize("stage", ["getFile", "download"])
    @pytest.mark.parametrize("exc", [requests.ConnectionError, requests.Timeout, requests.exceptions.SSLError])
    def test_network_error_returns_502_not_500(self, client, known_file_id, stage, exc):
        secret_url = "https://api.telegram.org/botTEST_BOT_TOKEN_ABCDEF1234/getFile"
        effects = [exc(f"HTTPSConnectionPool: Max retries exceeded with url: {secret_url}")]
        if stage == "download":
            effects.insert(0, _tg_get_file())
        with patch("api.images.requests.get", side_effect=effects):
            resp = self._get(client)
        assert resp.status_code == 502

    @pytest.mark.parametrize("stage", ["getFile", "download"])
    def test_network_error_leaks_neither_the_token_nor_the_url(self, client, known_file_id, caplog, stage):
        """requests puts the full URL, bot token included, in its exception text."""
        import logging
        leak = "Max retries exceeded with url: /botTEST_BOT_TOKEN_ABCDEF1234/getFile"
        effects = [requests.ConnectionError(leak)]
        if stage == "download":
            effects.insert(0, _tg_get_file())
        with caplog.at_level(logging.WARNING), patch("api.images.requests.get", side_effect=effects):
            resp = self._get(client)
        assert "TEST_BOT_TOKEN" not in resp.get_data(as_text=True)
        assert "TEST_BOT_TOKEN" not in caplog.text  # nor in the log
        assert "ConnectionError" in caplog.text     # the type is enough to debug with

    def test_bot_token_is_not_leaked_in_response(self, client, known_file_id):
        with patch("api.images.requests.get", side_effect=[_tg_get_file(), _tg_binary()]):
            resp = self._get(client)
        assert b"TEST_BOT_TOKEN" not in resp.data
        assert "TEST_BOT_TOKEN" not in str(resp.headers)

    # --- what is allowed to come back -------------------------------------------------------

    @pytest.mark.parametrize("content_type", [
        "text/html", "text/html; charset=utf-8", "image/svg+xml", "IMAGE/SVG+XML",
        "application/javascript", "application/pdf", "text/plain",
    ])
    def test_non_image_content_is_refused(self, client, known_file_id, content_type):
        with patch("api.images.requests.get",
                   side_effect=[_tg_get_file(), _tg_binary(b"<script>alert(1)</script>", content_type=content_type)]):
            resp = self._get(client)
        assert resp.status_code == 502
        assert b"<script>" not in resp.data

    @pytest.mark.parametrize("content_type", [
        "image/jpeg", "image/png", "image/webp", "image/gif", "application/octet-stream",
        "image/jpeg; charset=binary",
    ])
    def test_real_images_are_served(self, client, known_file_id, content_type):
        with patch("api.images.requests.get",
                   side_effect=[_tg_get_file(), _tg_binary(content_type=content_type)]):
            assert self._get(client).status_code == 200

    def test_oversized_image_by_declared_length_is_refused(self, client, known_file_id):
        big = _tg_binary()
        big.headers = {"Content-Type": "image/png", "Content-Length": str(50 * 1024 * 1024)}
        with patch("api.images.requests.get", side_effect=[_tg_get_file(), big]):
            assert self._get(client).status_code == 502

    def test_oversized_image_by_actual_size_is_refused(self, client, known_file_id):
        big = _tg_binary(b"x" * (10 * 1024 * 1024 + 1))
        with patch("api.images.requests.get", side_effect=[_tg_get_file(), big]):
            assert self._get(client).status_code == 502

    def test_a_malformed_content_length_is_ignored_not_trusted(self, client, known_file_id):
        odd = _tg_binary()
        odd.headers = {"Content-Type": "image/png", "Content-Length": "not-a-number"}
        with patch("api.images.requests.get", side_effect=[_tg_get_file(), odd]):
            assert self._get(client).status_code == 200
