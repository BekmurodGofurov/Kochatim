"""
Unit tests — utils/device.py

User-Agent tahlili, IP aniqlash va ip-api.com orqali shahar izlash.
Tashqi HTTP so'rov hech qachon haqiqatda ketmaydi.
"""
from unittest.mock import MagicMock, patch

import pytest
import requests

from utils.device import _browser, _os, get_city, get_client_ip, parse_device


# ─── _browser ─────────────────────────────────────────────────────────────────

class TestBrowser:
    @pytest.mark.parametrize("ua,expected", [
        ("Mozilla/5.0 (Linux; Android 13) SamsungBrowser/21.0 Chrome/110", "Samsung"),
        ("Mozilla/5.0 OPR/95.0.4635.46", "Opera"),
        ("Mozilla/5.0 Opera/9.80", "Opera"),
        ("Mozilla/5.0 Edg/120.0.0.0", "Edge"),
        ("Mozilla/5.0 EdgA/120.0.0.0", "Edge"),
        ("Mozilla/5.0 Firefox/121.0", "Firefox"),
        ("Mozilla/5.0 FxiOS/121.0", "Firefox"),
        ("Mozilla/5.0 Chrome/120.0.0.0 Safari/537.36", "Chrome"),
        ("Mozilla/5.0 CriOS/120.0.0.0", "Chrome"),
        ("Mozilla/5.0 (Macintosh) Version/17.0 Safari/605.1.15", "Safari"),
    ])
    def test_known_browsers(self, ua, expected):
        assert _browser(ua) == expected

    def test_unknown_returns_generic_label(self):
        assert _browser("curl/8.4.0") == "Browser"

    def test_empty_string_returns_generic_label(self):
        assert _browser("") == "Browser"

    def test_samsung_wins_over_chrome(self):
        # SamsungBrowser UA ichida Chrome/ ham bor — tartib muhim
        ua = "Mozilla/5.0 (Linux; Android) SamsungBrowser/21.0 Chrome/110 Safari/537.36"
        assert _browser(ua) == "Samsung"

    def test_edge_wins_over_chrome(self):
        ua = "Mozilla/5.0 Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
        assert _browser(ua) == "Edge"

    def test_chrome_wins_over_safari(self):
        # Chrome UA har doim Safari/ ni ham o'z ichiga oladi
        ua = "Mozilla/5.0 Chrome/120.0.0.0 Safari/537.36"
        assert _browser(ua) == "Chrome"


# ─── _os ──────────────────────────────────────────────────────────────────────

class TestOs:
    @pytest.mark.parametrize("ua,expected", [
        ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0)", "iPhone"),
        ("Mozilla/5.0 (iPad; CPU OS 17_0)", "iPad"),
        ("Mozilla/5.0 (Linux; Android 13; Pixel 7)", "Android"),
        ("Mozilla/5.0 (Linux; Android 13; Tablet)", "Android Tablet"),
        ("Mozilla/5.0 (Linux; Android 13; SM-Tab)", "Android Tablet"),
        ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)", "macOS"),
        ("Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Windows"),
        ("Mozilla/5.0 (X11; Linux x86_64)", "Linux"),
    ])
    def test_known_platforms(self, ua, expected):
        assert _os(ua) == expected

    def test_unknown_returns_empty_string(self):
        assert _os("curl/8.4.0") == ""

    def test_empty_string_returns_empty_string(self):
        assert _os("") == ""

    def test_android_checked_before_linux(self):
        # Android UA ichida "Linux" ham bor
        assert _os("Mozilla/5.0 (Linux; Android 13)") == "Android"


# ─── parse_device ─────────────────────────────────────────────────────────────

class TestParseDevice:
    def test_browser_and_os_joined(self):
        ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/120 Safari/537.36"
        assert parse_device(ua) == "Chrome macOS"

    def test_iphone_safari(self):
        ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0) Version/17.0 Safari/605.1.15"
        assert parse_device(ua) == "Safari iPhone"

    def test_browser_only_when_os_unknown(self):
        assert parse_device("Mozilla/5.0 Firefox/121.0") == "Firefox"

    def test_empty_user_agent(self):
        assert parse_device("") == "Browser"

    def test_none_user_agent_does_not_raise(self):
        # `ua = user_agent or ""` — None xavfsiz ishlanadi
        assert parse_device(None) == "Browser"

    def test_never_returns_empty_string(self):
        # Sessiya ro'yxatida bo'sh label ko'rinmasligi kerak
        for ua in ("", None, "junk", "curl/8"):
            assert parse_device(ua).strip() != ""


# ─── get_client_ip ────────────────────────────────────────────────────────────

def _fake_request(headers=None, remote_addr=None):
    req = MagicMock()
    req.headers = headers or {}
    req.remote_addr = remote_addr
    return req


class TestGetClientIp:
    def test_uses_remote_addr_when_no_xff(self):
        req = _fake_request(remote_addr="203.0.113.7")
        assert get_client_ip(req) == "203.0.113.7"

    def test_prefers_x_forwarded_for(self):
        req = _fake_request(
            headers={"X-Forwarded-For": "198.51.100.5"},
            remote_addr="10.0.0.1",
        )
        assert get_client_ip(req) == "198.51.100.5"

    def test_takes_first_ip_from_xff_chain(self):
        req = _fake_request(
            headers={"X-Forwarded-For": "198.51.100.5, 10.0.0.1, 172.16.0.1"},
            remote_addr="10.0.0.1",
        )
        assert get_client_ip(req) == "198.51.100.5"

    def test_strips_whitespace_in_xff(self):
        req = _fake_request(headers={"X-Forwarded-For": "  198.51.100.5  , 10.0.0.1"})
        assert get_client_ip(req) == "198.51.100.5"

    def test_empty_xff_falls_back_to_remote_addr(self):
        req = _fake_request(headers={"X-Forwarded-For": ""}, remote_addr="10.0.0.9")
        assert get_client_ip(req) == "10.0.0.9"

    def test_returns_empty_string_when_nothing_available(self):
        req = _fake_request(remote_addr=None)
        assert get_client_ip(req) == ""


# ─── get_city ─────────────────────────────────────────────────────────────────

class TestGetCity:
    @pytest.mark.parametrize("ip", ["", None, "127.0.0.1", "::1"])
    def test_local_and_empty_ips_skip_lookup(self, ip):
        with patch("utils.device._requests.get") as mock_get:
            assert get_city(ip) == ""
        mock_get.assert_not_called()

    def test_successful_lookup_returns_city(self):
        resp = MagicMock()
        resp.json.return_value = {"status": "success", "city": "Toshkent"}
        with patch("utils.device._requests.get", return_value=resp):
            assert get_city("203.0.113.7") == "Toshkent"

    def test_sends_ip_in_url(self):
        resp = MagicMock()
        resp.json.return_value = {"status": "success", "city": "Samarqand"}
        with patch("utils.device._requests.get", return_value=resp) as mock_get:
            get_city("203.0.113.7")
        assert "203.0.113.7" in mock_get.call_args[0][0]

    def test_uses_a_timeout(self):
        # Sessiya yaratish yo'lida — timeout bo'lmasa login osilib qoladi
        resp = MagicMock()
        resp.json.return_value = {"status": "success", "city": "Buxoro"}
        with patch("utils.device._requests.get", return_value=resp) as mock_get:
            get_city("203.0.113.7")
        assert mock_get.call_args.kwargs["timeout"] > 0

    def test_failed_status_returns_empty(self):
        resp = MagicMock()
        resp.json.return_value = {"status": "fail", "message": "private range"}
        with patch("utils.device._requests.get", return_value=resp):
            assert get_city("10.0.0.1") == ""

    def test_missing_city_field_returns_empty(self):
        resp = MagicMock()
        resp.json.return_value = {"status": "success"}
        with patch("utils.device._requests.get", return_value=resp):
            assert get_city("203.0.113.7") == ""

    def test_null_city_returns_empty_string_not_none(self):
        resp = MagicMock()
        resp.json.return_value = {"status": "success", "city": None}
        with patch("utils.device._requests.get", return_value=resp):
            assert get_city("203.0.113.7") == ""

    def test_timeout_returns_empty_string(self):
        with patch("utils.device._requests.get",
                   side_effect=requests.Timeout("too slow")):
            assert get_city("203.0.113.7") == ""

    def test_connection_error_returns_empty_string(self):
        with patch("utils.device._requests.get",
                   side_effect=requests.ConnectionError("no route")):
            assert get_city("203.0.113.7") == ""

    def test_invalid_json_returns_empty_string(self):
        resp = MagicMock()
        resp.json.side_effect = ValueError("not json")
        with patch("utils.device._requests.get", return_value=resp):
            assert get_city("203.0.113.7") == ""
