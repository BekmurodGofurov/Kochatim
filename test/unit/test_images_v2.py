"""
Unit tests — utils/images_v2.py

ImgBB ga yuklash va Telegram file_id -> ImgBB URL konvertatsiyasi.
Hamma tashqi HTTP chaqiruvi mock qilinadi.

Bu modulning markaziy qoidasi: xatolik yuz berganda hech qachon
exception ko'tarmaydi — None yoki originalni qaytaradi.
"""
import base64
from unittest.mock import MagicMock, patch

import pytest
import requests

from utils.images_v2 import process_image_input, telegram_to_imgbb, upload_to_imgbb

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"fake image data"


def _json_response(payload, status=200):
    resp = MagicMock()
    resp.json.return_value = payload
    resp.status_code = status
    resp.content = PNG_BYTES
    return resp


# ─── upload_to_imgbb ──────────────────────────────────────────────────────────

class TestUploadToImgbb:
    def test_success_returns_url(self):
        resp = _json_response({"success": True, "data": {"url": "https://i.ibb.co/abc.png"}})
        with patch("utils.images_v2.requests.post", return_value=resp):
            assert upload_to_imgbb(PNG_BYTES) == "https://i.ibb.co/abc.png"

    def test_sends_base64_encoded_image(self):
        resp = _json_response({"success": True, "data": {"url": "https://i.ibb.co/a.png"}})
        with patch("utils.images_v2.requests.post", return_value=resp) as mock_post:
            upload_to_imgbb(PNG_BYTES)
        sent = mock_post.call_args.kwargs["data"]["image"]
        assert base64.b64decode(sent) == PNG_BYTES

    def test_sends_api_key(self):
        resp = _json_response({"success": True, "data": {"url": "https://i.ibb.co/a.png"}})
        with patch("utils.images_v2.requests.post", return_value=resp) as mock_post:
            upload_to_imgbb(PNG_BYTES)
        assert mock_post.call_args.kwargs["data"]["key"] == "test-imgbb-api-key"

    def test_uses_a_timeout(self):
        resp = _json_response({"success": True, "data": {"url": "https://i.ibb.co/a.png"}})
        with patch("utils.images_v2.requests.post", return_value=resp) as mock_post:
            upload_to_imgbb(PNG_BYTES)
        assert mock_post.call_args.kwargs["timeout"] > 0

    def test_missing_api_key_returns_none_without_request(self):
        with patch("utils.images_v2.Config.IMGBB_API_KEY", ""), \
             patch("utils.images_v2.requests.post") as mock_post:
            assert upload_to_imgbb(PNG_BYTES) is None
        mock_post.assert_not_called()

    def test_unsuccessful_response_returns_none(self):
        resp = _json_response({"success": False, "error": {"message": "rejected"}})
        with patch("utils.images_v2.requests.post", return_value=resp):
            assert upload_to_imgbb(PNG_BYTES) is None

    def test_timeout_returns_none(self):
        with patch("utils.images_v2.requests.post", side_effect=requests.Timeout()):
            assert upload_to_imgbb(PNG_BYTES) is None

    def test_connection_error_returns_none(self):
        with patch("utils.images_v2.requests.post", side_effect=requests.ConnectionError()):
            assert upload_to_imgbb(PNG_BYTES) is None

    def test_invalid_json_returns_none(self):
        resp = MagicMock()
        resp.json.side_effect = ValueError("not json")
        with patch("utils.images_v2.requests.post", return_value=resp):
            assert upload_to_imgbb(PNG_BYTES) is None

    def test_missing_url_field_returns_none(self):
        resp = _json_response({"success": True, "data": {}})
        with patch("utils.images_v2.requests.post", return_value=resp):
            assert upload_to_imgbb(PNG_BYTES) is None

    def test_empty_bytes_still_attempts_upload(self):
        resp = _json_response({"success": True, "data": {"url": "https://i.ibb.co/e.png"}})
        with patch("utils.images_v2.requests.post", return_value=resp):
            assert upload_to_imgbb(b"") == "https://i.ibb.co/e.png"


# ─── telegram_to_imgbb ────────────────────────────────────────────────────────

class TestTelegramToImgbb:
    FILE_ID = "AgACAgIAAxkBAAIBY2Z"

    def test_success_returns_imgbb_url(self):
        get_file = _json_response({"ok": True, "result": {"file_path": "photos/f.jpg"}})
        download = _json_response({}, status=200)
        upload = _json_response({"success": True, "data": {"url": "https://i.ibb.co/x.png"}})
        with patch("utils.images_v2.requests.get", side_effect=[get_file, download]), \
             patch("utils.images_v2.requests.post", return_value=upload):
            assert telegram_to_imgbb(self.FILE_ID) == "https://i.ibb.co/x.png"

    def test_missing_bot_token_returns_none_without_request(self):
        with patch("utils.images_v2.Config.BOT_TOKEN", ""), \
             patch("utils.images_v2.requests.get") as mock_get:
            assert telegram_to_imgbb(self.FILE_ID) is None
        mock_get.assert_not_called()

    def test_get_file_not_ok_returns_none(self):
        get_file = _json_response({"ok": False, "description": "file not found"})
        with patch("utils.images_v2.requests.get", return_value=get_file):
            assert telegram_to_imgbb(self.FILE_ID) is None

    def test_missing_file_path_returns_none(self):
        get_file = _json_response({"ok": True, "result": {}})
        with patch("utils.images_v2.requests.get", return_value=get_file):
            assert telegram_to_imgbb(self.FILE_ID) is None

    def test_download_non_200_returns_none(self):
        get_file = _json_response({"ok": True, "result": {"file_path": "photos/f.jpg"}})
        download = _json_response({}, status=404)
        with patch("utils.images_v2.requests.get", side_effect=[get_file, download]):
            assert telegram_to_imgbb(self.FILE_ID) is None

    def test_imgbb_failure_propagates_as_none(self):
        get_file = _json_response({"ok": True, "result": {"file_path": "photos/f.jpg"}})
        download = _json_response({}, status=200)
        upload = _json_response({"success": False})
        with patch("utils.images_v2.requests.get", side_effect=[get_file, download]), \
             patch("utils.images_v2.requests.post", return_value=upload):
            assert telegram_to_imgbb(self.FILE_ID) is None

    def test_network_error_returns_none(self):
        with patch("utils.images_v2.requests.get", side_effect=requests.ConnectionError()):
            assert telegram_to_imgbb(self.FILE_ID) is None

    def test_file_id_sent_to_telegram(self):
        get_file = _json_response({"ok": True, "result": {"file_path": "photos/f.jpg"}})
        download = _json_response({}, status=200)
        upload = _json_response({"success": True, "data": {"url": "https://i.ibb.co/x.png"}})
        with patch("utils.images_v2.requests.get", side_effect=[get_file, download]) as mock_get, \
             patch("utils.images_v2.requests.post", return_value=upload):
            telegram_to_imgbb(self.FILE_ID)
        assert mock_get.call_args_list[0].kwargs["params"] == {"file_id": self.FILE_ID}

    def test_bot_token_not_leaked_into_returned_url(self):
        """Qaytarilgan URL ImgBB ga tegishli — Telegram tokeni ichida bo'lmasligi kerak."""
        get_file = _json_response({"ok": True, "result": {"file_path": "photos/f.jpg"}})
        download = _json_response({}, status=200)
        upload = _json_response({"success": True, "data": {"url": "https://i.ibb.co/x.png"}})
        with patch("utils.images_v2.requests.get", side_effect=[get_file, download]), \
             patch("utils.images_v2.requests.post", return_value=upload):
            url = telegram_to_imgbb(self.FILE_ID)
        assert "TEST_BOT_TOKEN" not in url


# ─── process_image_input ──────────────────────────────────────────────────────

class TestProcessImageInput:
    def test_https_url_passed_through_untouched(self):
        url = "https://example.com/a.png"
        with patch("utils.images_v2.telegram_to_imgbb") as mock_tg:
            assert process_image_input(url) == url
        mock_tg.assert_not_called()

    def test_http_url_passed_through_untouched(self):
        url = "http://example.com/a.png"
        with patch("utils.images_v2.telegram_to_imgbb") as mock_tg:
            assert process_image_input(url) == url
        mock_tg.assert_not_called()

    def test_file_id_converted_to_imgbb_url(self):
        with patch("utils.images_v2.telegram_to_imgbb",
                   return_value="https://i.ibb.co/y.png"):
            assert process_image_input("AgACAgIAAxk") == "https://i.ibb.co/y.png"

    def test_falls_back_to_original_when_conversion_fails(self):
        with patch("utils.images_v2.telegram_to_imgbb", return_value=None):
            assert process_image_input("AgACAgIAAxk") == "AgACAgIAAxk"

    def test_empty_string_returned_as_is(self):
        with patch("utils.images_v2.telegram_to_imgbb") as mock_tg:
            assert process_image_input("") == ""
        mock_tg.assert_not_called()

    def test_none_returned_as_is(self):
        with patch("utils.images_v2.telegram_to_imgbb") as mock_tg:
            assert process_image_input(None) is None
        mock_tg.assert_not_called()

    def test_network_failure_falls_back_to_original(self):
        """
        process_image_input o'zida try/except tutmaydi — xatolikni ushlash
        telegram_to_imgbb ning vazifasi. Shuning uchun tarmoq uzilganda
        ham original qiymat qaytadi, exception emas.
        """
        with patch("utils.images_v2.requests.get",
                   side_effect=requests.ConnectionError("no route")):
            assert process_image_input("AgACAgIAAxk") == "AgACAgIAAxk"

    def test_url_with_uppercase_scheme_is_treated_as_file_id(self):
        # Tekshiruv startswith("http") — "HTTPS://" mos kelmaydi.
        # Hujjatlashtirilgan cheklov, kutilmagan hol emas.
        with patch("utils.images_v2.telegram_to_imgbb", return_value=None) as mock_tg:
            assert process_image_input("HTTPS://e.com/a.png") == "HTTPS://e.com/a.png"
        mock_tg.assert_called_once()
