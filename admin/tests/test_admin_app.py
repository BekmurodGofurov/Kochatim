"""
Tests — admin/app.py

Admin panel Redis'ni yagona ma'lumot manbai sifatida ishlatadi: backend
`req_count:<sana>` va `endpoint_stats` kalitlarini yozadi, panel ularni
o'qiydi. Shuning uchun kalit nomlari ikki servis orasidagi shartnoma —
testlar ularni aynan tekshiradi.
"""
import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
import redis as redis_lib

from conftest import basic_auth


def today():
    return datetime.utcnow().date()


def req_key(d):
    return f"req_count:{d}"


# ─── GET / ────────────────────────────────────────────────────────────────────

class TestIndex:
    def test_returns_200(self, client):
        assert client.get("/").status_code == 200

    def test_renders_html(self, client):
        resp = client.get("/")
        assert resp.content_type.startswith("text/html")

    def test_body_is_not_empty(self, client):
        assert len(client.get("/").data) > 0


# ─── request_counts ───────────────────────────────────────────────────────────

class TestRequestCounts:
    def test_zero_when_redis_empty(self, module):
        stats = module.request_counts()
        assert stats["today"]["total"] == 0
        assert stats["this_week"]["total"] == 0

    def test_counts_today(self, module, redis_conn):
        redis_conn.set(req_key(today()), 42)
        stats = module.request_counts()
        assert stats["today"]["total"] == 42

    def test_week_total_sums_days_since_monday(self, module, redis_conn):
        d = today()
        week_start = d - timedelta(days=d.weekday())
        days = [week_start + timedelta(days=i) for i in range((d - week_start).days + 1)]
        for day in days:
            redis_conn.set(req_key(day), 10)
        stats = module.request_counts()
        assert stats["this_week"]["total"] == 10 * len(days)

    def test_today_is_the_last_day_of_the_window(self, module, redis_conn):
        d = today()
        week_start = d - timedelta(days=d.weekday())
        redis_conn.set(req_key(week_start), 5)
        redis_conn.set(req_key(d), 7)
        stats = module.request_counts()
        assert stats["today"]["total"] == 7

    def test_missing_days_count_as_zero(self, module, redis_conn):
        redis_conn.set(req_key(today()), 3)
        stats = module.request_counts()
        assert stats["this_week"]["total"] >= 3

    def test_shape_is_stable(self, module):
        stats = module.request_counts()
        assert set(stats) == {"today", "this_week"}
        assert set(stats["today"]) == {"total"}

    def test_redis_failure_returns_zeroes_not_an_error(self, module):
        """
        Panel Redis o'chganda ham yuklanishi kerak — nol ko'rsatadi,
        500 bermaydi.
        """
        with patch.object(module.redis_client, "mget",
                          side_effect=redis_lib.ConnectionError("down")):
            stats = module.request_counts()
        assert stats["today"]["total"] == 0
        assert stats["this_week"]["total"] == 0

    def test_non_numeric_value_is_handled(self, module, redis_conn):
        redis_conn.set(req_key(today()), "not-a-number")
        stats = module.request_counts()
        # int() yiqiladi -> except bloki nolni qaytaradi
        assert stats["today"]["total"] == 0


# ─── GET /api/stats ───────────────────────────────────────────────────────────

class TestGetStats:
    URL = "/api/stats"

    def test_returns_200_and_json(self, client):
        resp = client.get(self.URL)
        assert resp.status_code == 200
        assert resp.content_type.startswith("application/json")

    def test_payload_shape(self, client):
        data = client.get(self.URL).get_json()
        assert set(data) == {"logs", "endpoints"}

    def test_empty_redis_gives_empty_endpoints(self, client):
        data = client.get(self.URL).get_json()
        assert data["endpoints"] == []

    def test_reports_endpoint_counts(self, client, redis_conn):
        redis_conn.zincrby("endpoint_stats", 5, "/api/me")
        redis_conn.zincrby("endpoint_stats", 2, "/api/sales")
        data = client.get(self.URL).get_json()
        assert {"path": "/api/me", "count": 5} in data["endpoints"]
        assert {"path": "/api/sales", "count": 2} in data["endpoints"]

    def test_endpoints_sorted_by_count_descending(self, client, redis_conn):
        redis_conn.zincrby("endpoint_stats", 1, "/api/low")
        redis_conn.zincrby("endpoint_stats", 99, "/api/high")
        data = client.get(self.URL).get_json()
        assert data["endpoints"][0]["path"] == "/api/high"

    def test_returns_at_most_ten_endpoints(self, client, redis_conn):
        for i in range(25):
            redis_conn.zincrby("endpoint_stats", i + 1, f"/api/p{i}")
        data = client.get(self.URL).get_json()
        assert len(data["endpoints"]) == 10

    def test_counts_are_ints_not_floats(self, client, redis_conn):
        """Redis sorted set ball float qaytaradi — JSON da 5 bo'lishi kerak, 5.0 emas."""
        redis_conn.zincrby("endpoint_stats", 5, "/api/me")
        data = client.get(self.URL).get_json()
        assert isinstance(data["endpoints"][0]["count"], int)

    def test_includes_log_stats(self, client, redis_conn):
        redis_conn.set(req_key(today()), 11)
        data = client.get(self.URL).get_json()
        assert data["logs"]["today"]["total"] == 11

    def test_redis_failure_returns_200_with_empty_endpoints(self, client, module):
        with patch.object(module.redis_client, "zrevrangebyscore",
                          side_effect=redis_lib.ConnectionError("down")):
            resp = client.get(self.URL)
        assert resp.status_code == 200
        assert resp.get_json()["endpoints"] == []

    def test_needs_auth(self, anon_client):
        """Was test_needs_no_auth: the panel used to answer anyone who could reach port 9000."""
        assert anon_client.get(self.URL).status_code == 401


# ─── redis_listener ───────────────────────────────────────────────────────────

class _StopListening(Exception):
    """Cheksiz pubsub tsiklini to'xtatish uchun."""


def _pubsub_yielding(messages):
    """listen() berilgan xabarlarni qaytaradigan fake pubsub."""
    pubsub = MagicMock()
    pubsub.listen.return_value = iter(messages)
    return pubsub


class TestRedisListener:
    def test_subscribes_to_both_channels(self, module):
        pubsub = _pubsub_yielding([])
        with patch.object(module.redis_client, "pubsub", return_value=pubsub):
            module.redis_listener()
        channels = pubsub.subscribe.call_args[0][0]
        assert "server_metrics" in channels
        assert "live_requests" in channels

    def test_metrics_message_emitted_as_metrics_event(self, module, socketio):
        payload = {"server": "s1", "cpu": 10.0, "ram": 20.0}
        pubsub = _pubsub_yielding([
            {"type": "message", "channel": "server_metrics", "data": json.dumps(payload)},
        ])
        with patch.object(module.redis_client, "pubsub", return_value=pubsub):
            module.redis_listener()
        socketio.emit.assert_called_once_with("metrics", payload)

    def test_live_request_emitted_as_live_request_event(self, module, socketio):
        payload = {"path": "/api/me", "method": "GET", "status": 200}
        pubsub = _pubsub_yielding([
            {"type": "message", "channel": "live_requests", "data": json.dumps(payload)},
        ])
        with patch.object(module.redis_client, "pubsub", return_value=pubsub):
            module.redis_listener()
        socketio.emit.assert_called_once_with("live_request", payload)

    def test_subscribe_confirmations_are_ignored(self, module, socketio):
        pubsub = _pubsub_yielding([
            {"type": "subscribe", "channel": "server_metrics", "data": 1},
        ])
        with patch.object(module.redis_client, "pubsub", return_value=pubsub):
            module.redis_listener()
        socketio.emit.assert_not_called()

    def test_unknown_channel_is_ignored(self, module, socketio):
        pubsub = _pubsub_yielding([
            {"type": "message", "channel": "other", "data": json.dumps({"x": 1})},
        ])
        with patch.object(module.redis_client, "pubsub", return_value=pubsub):
            module.redis_listener()
        socketio.emit.assert_not_called()

    def test_invalid_json_does_not_stop_the_listener(self, module, socketio):
        """
        Listener daemon thread — bitta buzuq xabar uni o'ldirsa, panel
        jimgina muzlab qoladi va buni hech kim sezmaydi.
        """
        good = {"cpu": 5.0}
        pubsub = _pubsub_yielding([
            {"type": "message", "channel": "server_metrics", "data": "{broken"},
            {"type": "message", "channel": "server_metrics", "data": json.dumps(good)},
        ])
        with patch.object(module.redis_client, "pubsub", return_value=pubsub):
            module.redis_listener()
        socketio.emit.assert_called_once_with("metrics", good)

    def test_processes_several_messages_in_order(self, module, socketio):
        pubsub = _pubsub_yielding([
            {"type": "message", "channel": "server_metrics", "data": json.dumps({"cpu": 1})},
            {"type": "message", "channel": "live_requests", "data": json.dumps({"path": "/a"})},
        ])
        with patch.object(module.redis_client, "pubsub", return_value=pubsub):
            module.redis_listener()
        assert [c[0][0] for c in socketio.emit.call_args_list] == ["metrics", "live_request"]


# ─── Redis ulanish sozlamalari ───────────────────────────────────────────────

class TestRedisConfiguration:
    def test_decodes_responses(self, module):
        """
        decode_responses=True bo'lmasa json.loads bytes oladi va
        kanal nomlari b'server_metrics' bo'lib solishtirish buziladi.
        """
        assert module.redis_client.connection_pool.connection_kwargs.get(
            "decode_responses"
        ) is True


# ─── Authentication ───────────────────────────────────────────────────────────

class TestAuthentication:
    PATHS = ["/", "/api/stats", "/static/script.js", "/static/style.css", "/nope", "/socket.io/"]

    @pytest.mark.parametrize("path", PATHS)
    def test_no_credentials_is_401_with_a_challenge(self, anon_client, path):
        resp = anon_client.get(path)
        assert resp.status_code == 401
        assert resp.headers["WWW-Authenticate"].startswith("Basic")

    @pytest.mark.parametrize("path", ["/", "/api/stats", "/static/script.js"])
    def test_correct_credentials_are_accepted(self, anon_client, path):
        assert anon_client.get(path, headers=basic_auth()).status_code == 200

    @pytest.mark.parametrize("user,password", [
        ("test-admin", "wrong"), ("wrong", "test-password-123"), ("wrong", "wrong"),
        ("", ""), ("test-admin", ""), ("", "test-password-123"),
        ("test-admin", "test-password-123 "), ("TEST-ADMIN", "test-password-123"),
        ("test-admin:test-password-123", "x"),
    ])
    def test_wrong_credentials_are_401(self, anon_client, user, password):
        assert anon_client.get("/api/stats", headers=basic_auth(user, password)).status_code == 401

    @pytest.mark.parametrize("header", [
        "Bearer test-password-123", "Basic", "Basic !!!notbase64!!!", "Basic dGVzdA==",
        "Digest username=test-admin", "test-admin:test-password-123",
    ])
    def test_malformed_or_other_schemes_are_401(self, anon_client, header):
        assert anon_client.get("/api/stats", headers={"Authorization": header}).status_code == 401

    def test_unauthenticated_requests_never_reach_redis(self, anon_client, module):
        with patch.object(module.redis_client, "zrevrangebyscore") as zr:
            anon_client.get("/api/stats")
        zr.assert_not_called()

    def test_unauthenticated_response_reveals_no_stats(self, anon_client, redis_conn):
        redis_conn.zincrby("endpoint_stats", 5, "/api/secret-looking")
        assert b"secret-looking" not in anon_client.get("/api/stats").data

    def test_both_halves_are_always_compared(self, anon_client, module):
        """Constant time: a wrong username must not skip the password comparison."""
        with patch("app.hmac.compare_digest", return_value=False) as cmp:
            anon_client.get("/api/stats", headers=basic_auth("wrong", "wrong"))
        assert cmp.call_count == 2

    def test_fails_closed_when_no_password_is_configured(self, anon_client, module):
        with patch.object(module, "ADMIN_PASSWORD", ""):
            for path in ("/", "/api/stats"):
                assert anon_client.get(path, headers=basic_auth("test-admin", "")).status_code == 503
                assert anon_client.get(path, headers=basic_auth()).status_code == 503

    def test_fails_closed_when_no_username_is_configured(self, anon_client, module):
        with patch.object(module, "ADMIN_USER", ""):
            assert anon_client.get("/api/stats", headers=basic_auth("", "test-password-123")).status_code == 503

    def test_blank_credentials_never_match_blank_config(self, anon_client, module):
        with patch.object(module, "ADMIN_USER", ""), patch.object(module, "ADMIN_PASSWORD", ""):
            assert not module._authorized(MagicMock(authorization=None))
            req = MagicMock()
            req.authorization = MagicMock(type="basic", username="", password="")
            assert not module._authorized(req)


class TestLiveFeedAuthentication:
    """Socket.IO traffic bypasses before_request, so the connect handler must check."""

    def _connect(self, module, app, headers=None):
        with app.test_request_context("/socket.io/", headers=headers or {}):
            return module.handle_connect()

    def test_authenticated_operator_may_connect(self, module, app):
        assert self._connect(module, app, basic_auth()) is None  # None == accept

    def test_anonymous_connection_is_refused(self, module, app):
        assert self._connect(module, app) is False

    def test_wrong_password_is_refused(self, module, app):
        assert self._connect(module, app, basic_auth("test-admin", "nope")) is False

    def test_refused_when_the_panel_has_no_password(self, module, app):
        with patch.object(module, "ADMIN_PASSWORD", ""):
            assert self._connect(module, app, basic_auth()) is False

    def test_handler_is_registered_for_the_connect_event(self, module):
        module.socketio.on.assert_any_call("connect")

    def test_websocket_origins_are_same_origin_only_by_default(self, module):
        """A cross-site page must not ride the operator's cached Basic credentials."""
        assert module.ALLOWED_ORIGINS == []
        assert module.SocketIO.call_args.kwargs["cors_allowed_origins"] is None

    def test_no_wildcard_origin_anywhere(self):
        import pathlib
        src = (pathlib.Path(__file__).parent.parent / "app.py").read_text()
        assert 'cors_allowed_origins="*"' not in src and "cors_allowed_origins='*'" not in src


class TestHardening:
    def test_security_headers_are_set(self, client):
        h = client.get("/").headers
        assert h["X-Content-Type-Options"] == "nosniff"
        assert h["X-Frame-Options"] == "DENY"
        assert h["Referrer-Policy"] == "no-referrer"
        assert "no-store" in h["Cache-Control"]

    def test_headers_are_set_on_errors_too(self, anon_client):
        assert anon_client.get("/api/stats").headers["X-Content-Type-Options"] == "nosniff"

    def test_csp_allows_no_inline_or_eval_script(self, client):
        csp = client.get("/").headers["Content-Security-Policy"]
        script_src = next(p for p in csp.split(";") if p.strip().startswith("script-src"))
        assert "'unsafe-inline'" not in script_src and "'unsafe-eval'" not in script_src
        assert "frame-ancestors 'none'" in csp

    def test_csp_covers_exactly_the_scripts_the_page_loads(self, client):
        import re
        html = client.get("/").get_data(as_text=True)
        csp = client.get("/").headers["Content-Security-Policy"]
        for src in re.findall(r'<script[^>]+src="(https://[^"/]+)', html):
            assert src in csp, f"{src} is loaded by the page but not allowed by the CSP"

    def test_page_has_no_inline_script_the_csp_would_block(self, client):
        import re
        html = client.get("/").get_data(as_text=True)
        assert not re.search(r"<script(?![^>]*\bsrc=)[^>]*>\s*\S", html)
        assert not re.search(r"\son\w+\s*=", html)  # no onclick= and friends

    def test_debug_mode_is_never_hard_coded_on(self):
        import pathlib
        src = (pathlib.Path(__file__).parent.parent / "app.py").read_text()
        assert "debug=True" not in src


class TestFrontendNeverBuildsMarkupFromServerData:
    """
    The request path in the live feed and the top-10 table is chosen by
    whoever sent the request. Putting it through innerHTML is stored XSS in
    the operator's browser (and the panel sits on their internal network).
    """
    def _script(self):
        import pathlib
        return (pathlib.Path(__file__).parent.parent / "static" / "script.js").read_text()

    def test_script_never_uses_innerhtml(self):
        assert "innerHTML" not in self._script()

    def test_script_never_uses_other_html_sinks(self):
        src = self._script()
        for sink in ("outerHTML", "insertAdjacentHTML", "document.write", "eval(", "new Function"):
            assert sink not in src, sink
