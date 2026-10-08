"""
Unit tests — utils/telegram_images.py va utils/telegram_notify.py

Ikkala modul ham "jimgina muvaffaqiyatsizlik" qoidasiga bo'ysunadi:
Telegram javob bermasa, so'rov yiqilmaydi.
"""
import json
from unittest.mock import MagicMock, patch

import pytest
import requests

import utils.telegram_images as tg_images
from utils.telegram_images import _bot_token, file_id_to_web_url
from utils.telegram_notify import send_message

FILE_ID = "AgACAgIAAxkBAAIBY2Z"


@pytest.fixture(autouse=True)
def clear_file_path_cache():
    """
    Modul darajasidagi _FILE_PATH_CACHE testlar orasida saqlanib qoladi
    va keyingi testlarni buzadi — har test oldidan tozalanadi.
    """
    tg_images._FILE_PATH_CACHE.clear()
    yield
    tg_images._FILE_PATH_CACHE.clear()


def _urlopen_cm(payload):
    """urllib.request.urlopen context manager ini taqlid qiladi."""
    resp = MagicMock()
    resp.read.return_value = json.dumps(payload).encode("utf-8")
    cm = MagicMock()
    cm.__enter__.return_value = resp
    cm.__exit__.return_value = False
    return cm


# ─── _bot_token ───────────────────────────────────────────────────────────────

class TestBotToken:
    def test_reads_bot_token_env(self):
        assert _bot_token() == "123456789:TEST_BOT_TOKEN_ABCDEF1234"

    def test_missing_env_returns_empty_string(self):
        with patch.dict("os.environ", {"BOT_TOKEN": ""}):
            assert _bot_token() == ""


# ─── file_id_to_web_url ───────────────────────────────────────────────────────

class TestFileIdToWebUrl:
    def test_success_returns_file_url(self):
        cm = _urlopen_cm({"ok": True, "result": {"file_path": "photos/file_1.jpg"}})
        with patch("utils.telegram_images.urllib.request.urlopen", return_value=cm):
            url = file_id_to_web_url(FILE_ID)
        assert url.endswith("/photos/file_1.jpg")
        assert url.startswith("https://api.telegram.org/file/bot")

    def test_empty_file_id_returns_none(self):
        with patch("utils.telegram_images.urllib.request.urlopen") as mock_open:
            assert file_id_to_web_url("") is None
        mock_open.assert_not_called()

    def test_none_file_id_returns_none(self):
        with patch("utils.telegram_images.urllib.request.urlopen") as mock_open:
            assert file_id_to_web_url(None) is None
        mock_open.assert_not_called()

    def test_missing_token_returns_none(self):
        with patch("utils.telegram_images._bot_token", return_value=""), \
             patch("utils.telegram_images.urllib.request.urlopen") as mock_open:
            assert file_id_to_web_url(FILE_ID) is None
        mock_open.assert_not_called()

    def test_not_ok_response_returns_none(self):
        cm = _urlopen_cm({"ok": False, "description": "file not found"})
        with patch("utils.telegram_images.urllib.request.urlopen", return_value=cm):
            assert file_id_to_web_url(FILE_ID) is None

    def test_missing_file_path_returns_none(self):
        cm = _urlopen_cm({"ok": True, "result": {}})
        with patch("utils.telegram_images.urllib.request.urlopen", return_value=cm):
            assert file_id_to_web_url(FILE_ID) is None

    def test_network_error_returns_none(self):
        with patch("utils.telegram_images.urllib.request.urlopen",
                   side_effect=OSError("unreachable")):
            assert file_id_to_web_url(FILE_ID) is None

    def test_invalid_json_returns_none(self):
        resp = MagicMock()
        resp.read.return_value = b"not json at all"
        cm = MagicMock()
        cm.__enter__.return_value = resp
        cm.__exit__.return_value = False
        with patch("utils.telegram_images.urllib.request.urlopen", return_value=cm):
            assert file_id_to_web_url(FILE_ID) is None

    def test_file_id_is_url_encoded_in_request(self):
        cm = _urlopen_cm({"ok": True, "result": {"file_path": "p/f.jpg"}})
        with patch("utils.telegram_images.urllib.request.urlopen", return_value=cm) as mock_open:
            file_id_to_web_url("id with spaces&amp")
        requested = mock_open.call_args[0][0]
        assert " " not in requested and "id+with+spaces" in requested


class TestFilePathCache:
    def test_second_call_is_served_from_cache(self):
        cm = _urlopen_cm({"ok": True, "result": {"file_path": "photos/f.jpg"}})
        with patch("utils.telegram_images.urllib.request.urlopen", return_value=cm) as mock_open:
            first = file_id_to_web_url(FILE_ID)
            second = file_id_to_web_url(FILE_ID)
        assert first == second
        mock_open.assert_called_once()

    def test_failure_is_cached_as_none(self):
        """Muvaffaqiyatsiz natija ham keshlanadi — getFile qayta urilmaydi."""
        cm = _urlopen_cm({"ok": False})
        with patch("utils.telegram_images.urllib.request.urlopen", return_value=cm) as mock_open:
            assert file_id_to_web_url(FILE_ID) is None
            assert file_id_to_web_url(FILE_ID) is None
        mock_open.assert_called_once()

    def test_network_error_is_cached_as_none(self):
        with patch("utils.telegram_images.urllib.request.urlopen",
                   side_effect=OSError("down")) as mock_open:
            assert file_id_to_web_url(FILE_ID) is None
            assert file_id_to_web_url(FILE_ID) is None
        mock_open.assert_called_once()

    def test_different_file_ids_cached_separately(self):
        cm1 = _urlopen_cm({"ok": True, "result": {"file_path": "a.jpg"}})
        cm2 = _urlopen_cm({"ok": True, "result": {"file_path": "b.jpg"}})
        with patch("utils.telegram_images.urllib.request.urlopen", side_effect=[cm1, cm2]):
            first = file_id_to_web_url("id-a")
            second = file_id_to_web_url("id-b")
        assert first.endswith("a.jpg") and second.endswith("b.jpg")


# ─── send_message ─────────────────────────────────────────────────────────────

class TestSendMessage:
    def test_posts_to_telegram_send_message(self):
        with patch("utils.telegram_notify.requests.post") as mock_post:
            send_message(111, "salom")
        url = mock_post.call_args[0][0]
        assert url.endswith("/sendMessage")

    def test_sends_chat_id_and_text(self):
        with patch("utils.telegram_notify.requests.post") as mock_post:
            send_message(111, "salom")
        body = mock_post.call_args.kwargs["json"]
        assert body["chat_id"] == 111
        assert body["text"] == "salom"

    def test_default_parse_mode_is_markdown(self):
        with patch("utils.telegram_notify.requests.post") as mock_post:
            send_message(111, "*bold*")
        assert mock_post.call_args.kwargs["json"]["parse_mode"] == "Markdown"

    def test_custom_parse_mode(self):
        with patch("utils.telegram_notify.requests.post") as mock_post:
            send_message(111, "<b>x</b>", parse_mode="HTML")
        assert mock_post.call_args.kwargs["json"]["parse_mode"] == "HTML"

    def test_uses_a_timeout(self):
        with patch("utils.telegram_notify.requests.post") as mock_post:
            send_message(111, "salom")
        assert mock_post.call_args.kwargs["timeout"] > 0

    def test_missing_token_sends_nothing(self):
        with patch("utils.telegram_notify.Config.BOT_TOKEN", ""), \
             patch("utils.telegram_notify.requests.post") as mock_post:
            send_message(111, "salom")
        mock_post.assert_not_called()

    @pytest.mark.parametrize("chat_id", [0, None])
    def test_falsy_chat_id_sends_nothing(self, chat_id):
        with patch("utils.telegram_notify.requests.post") as mock_post:
            send_message(chat_id, "salom")
        mock_post.assert_not_called()

    def test_returns_none(self):
        with patch("utils.telegram_notify.requests.post"):
            assert send_message(111, "salom") is None

    def test_timeout_is_swallowed(self):
        with patch("utils.telegram_notify.requests.post", side_effect=requests.Timeout()):
            send_message(111, "salom")  # ko'tarilmasligi kerak

    def test_connection_error_is_swallowed(self):
        """
        Hamkorni o'chirish yo'lida xabar yuboriladi — Telegram o'chgan
        bo'lsa ham API so'rovi 200 qaytishi kerak.
        """
        with patch("utils.telegram_notify.requests.post",
                   side_effect=requests.ConnectionError()):
            send_message(111, "salom")  # ko'tarilmasligi kerak
