"""
Integration tests — backend/app.py

/health, CORS siyosati, xato ishlovchilar, so'rov statistikasi va
system_monitor tsikli.

CORS bu yerda xavfsizlik chegarasi: `_cors_origin` ro'yxatda yo'q
origin uchun "null" qaytaradi, "*" EMAS — shuning uchun ruxsat
etilmagan sayt credential bilan so'rov yubora olmaydi.
"""
import json
from unittest.mock import MagicMock, patch

import pytest

from conftest import TEST_API_KEY

ALLOWED = "http://localhost:5173"
NOT_ALLOWED = "http://evil.example.com"


def subscribe_to(redis_conn, channel):
    """Kanalga ulanadi va "subscribe" tasdiq xabarini iste'mol qilib tashlaydi."""
    pubsub = redis_conn.pubsub()
    pubsub.subscribe(channel)
    pubsub.get_message(timeout=0.1)
    return pubsub


def drain(pubsub, polls=10):
    """
    Navbatdagi pubsub xabarlarini oqizib oladi.

    `pubsub.listen()` ishlatilmaydi — u bloklovchi generator va xabar
    kelmasa test abadiy osilib qoladi. None qaytganda tsikl uzilmaydi:
    `get_message` birinchi chaqiruvda xizmat xabarini iste'mol qilib
    None berishi mumkin, holbuki haqiqiy xabar navbatda turgan bo'ladi.
    """
    out = []
    for _ in range(polls):
        msg = pubsub.get_message(timeout=0.05)
        if msg is not None and msg.get("type") == "message":
            out.append(msg)
    return out


# ─── /health ──────────────────────────────────────────────────────────────────

class TestHealth:
    def test_returns_200(self, client):
        assert client.get("/health").status_code == 200

    def test_reports_status_up(self, client):
        data = client.get("/health").get_json()
        assert data["ok"] is True
        assert data["data"]["status"] == "up"

    def test_includes_server_name(self, client):
        data = client.get("/health").get_json()
        assert "server" in data["data"]

    def test_server_name_comes_from_env(self, client):
        with patch.dict("os.environ", {"SERVER_NAME": "kochatim-1"}):
            data = client.get("/health").get_json()
        assert data["data"]["server"] == "kochatim-1"

    def test_defaults_server_name_when_unset(self, client):
        env = {"SERVER_NAME": ""}
        with patch.dict("os.environ", env):
            data = client.get("/health").get_json()
        # getenv bo'sh satr qaytaradi — standart qiymat faqat kalit yo'q bo'lsa
        assert "server" in data["data"]

    def test_needs_no_auth(self, client):
        assert client.get("/health").status_code == 200

    def test_not_counted_in_endpoint_stats(self, client, redis_conn):
        """/health /api/ yoki /auth/ bilan boshlanmaydi — hisobga olinmaydi."""
        client.get("/health")
        assert redis_conn.zscore("endpoint_stats", "/health") is None


# ─── _cors_origin ─────────────────────────────────────────────────────────────

class TestCorsOriginHelper:
    def test_allowed_origin_echoed_back(self, app_module):
        assert app_module._cors_origin(ALLOWED) == ALLOWED

    def test_unknown_origin_becomes_null(self, app_module):
        assert app_module._cors_origin(NOT_ALLOWED) == "null"

    def test_empty_origin_becomes_null(self, app_module):
        assert app_module._cors_origin("") == "null"

    def test_never_returns_wildcard(self, app_module):
        """
        "*" credential'li so'rovlar bilan birga ishlamaydi va ishlasa
        har qanday sayt sessiya bilan so'rov yuborardi.
        """
        for origin in (ALLOWED, NOT_ALLOWED, "", "null"):
            assert app_module._cors_origin(origin) != "*"

    def test_match_is_exact_not_prefix(self, app_module):
        assert app_module._cors_origin(ALLOWED + ".evil.com") == "null"


# ─── CORS preflight (OPTIONS) ─────────────────────────────────────────────────

class TestCorsPreflight:
    def test_options_returns_204(self, client):
        resp = client.open("/api/categories", method="OPTIONS",
                           headers={"Origin": ALLOWED})
        assert resp.status_code == 204

    def test_preflight_echoes_allowed_origin(self, client):
        resp = client.open("/api/categories", method="OPTIONS",
                           headers={"Origin": ALLOWED})
        assert resp.headers["Access-Control-Allow-Origin"] == ALLOWED

    def test_preflight_rejects_unknown_origin(self, client):
        resp = client.open("/api/categories", method="OPTIONS",
                           headers={"Origin": NOT_ALLOWED})
        assert resp.headers["Access-Control-Allow-Origin"] == "null"

    def test_preflight_allows_credentials(self, client):
        resp = client.open("/api/categories", method="OPTIONS",
                           headers={"Origin": ALLOWED})
        assert resp.headers["Access-Control-Allow-Credentials"] == "true"

    def test_preflight_advertises_auth_headers(self, client):
        resp = client.open("/api/categories", method="OPTIONS",
                           headers={"Origin": ALLOWED})
        allowed = resp.headers["Access-Control-Allow-Headers"]
        assert "Authorization" in allowed and "X-API-KEY" in allowed

    def test_preflight_advertises_methods(self, client):
        resp = client.open("/api/categories", method="OPTIONS",
                           headers={"Origin": ALLOWED})
        methods = resp.headers["Access-Control-Allow-Methods"]
        for m in ("GET", "POST", "PUT", "PATCH", "DELETE"):
            assert m in methods

    def test_preflight_sets_vary_origin(self, client):
        """Vary: Origin bo'lmasa proksi bir origin javobini boshqasiga beradi."""
        resp = client.open("/api/categories", method="OPTIONS",
                           headers={"Origin": ALLOWED})
        assert "Origin" in resp.headers["Vary"]

    def test_preflight_skips_auth(self, client):
        """OPTIONS before_request da to'xtaydi — 401 bo'lmasligi kerak."""
        resp = client.open("/api/categories", method="OPTIONS",
                           headers={"Origin": ALLOWED})
        assert resp.status_code == 204


# ─── CORS javob sarlavhalari ──────────────────────────────────────────────────

class TestCorsResponseHeaders:
    def test_headers_added_to_normal_response(self, client):
        resp = client.get("/health", headers={"Origin": ALLOWED})
        assert resp.headers["Access-Control-Allow-Origin"] == ALLOWED

    def test_unknown_origin_gets_null_on_normal_response(self, client):
        resp = client.get("/health", headers={"Origin": NOT_ALLOWED})
        assert resp.headers["Access-Control-Allow-Origin"] == "null"

    def test_headers_added_to_401_response(self, client):
        """Xato javoblarda ham CORS kerak — brauzer xatoni o'qiy olishi uchun."""
        resp = client.get("/api/categories", headers={"Origin": ALLOWED})
        assert resp.status_code == 401
        assert resp.headers["Access-Control-Allow-Origin"] == ALLOWED

    def test_headers_added_to_404_response(self, client):
        resp = client.get("/api/no-such-route", headers={"Origin": ALLOWED})
        assert resp.headers["Access-Control-Allow-Origin"] == ALLOWED

    def test_no_origin_header_gets_null(self, client):
        resp = client.get("/health")
        assert resp.headers["Access-Control-Allow-Origin"] == "null"


# ─── Xato ishlovchilar ────────────────────────────────────────────────────────

class TestErrorHandlers:
    def test_unknown_route_returns_404_json(self, client):
        resp = client.get("/no-such-route")
        assert resp.status_code == 404
        data = resp.get_json()
        assert data["ok"] is False
        assert data["error"]["message"] == "Not found"

    def test_404_is_json_not_html(self, client):
        resp = client.get("/no-such-route")
        assert resp.content_type.startswith("application/json")

    def test_unhandled_exception_returns_500_json(self, client):
        with patch("api.public.fetch_all", side_effect=RuntimeError("boom")):
            resp = client.get("/api/v1/public/categories")
        assert resp.status_code == 500
        assert resp.get_json()["ok"] is False

    def test_method_not_allowed_is_handled(self, client):
        resp = client.delete("/health")
        assert resp.status_code in (404, 405, 500)
        assert resp.get_json() is not None


# ─── _record_endpoint_stats ───────────────────────────────────────────────────

class TestEndpointStats:
    def test_api_path_is_counted(self, client, redis_conn):
        client.get("/api/categories")  # 401, lekin after_request baribir ishlaydi
        assert redis_conn.zscore("endpoint_stats", "/api/categories") == 1

    def test_auth_path_is_counted(self, client, redis_conn):
        client.post("/auth/verify-code", json={"code": "bad"})
        assert redis_conn.zscore("endpoint_stats", "/auth/verify-code") == 1

    def test_repeat_calls_increment(self, client, redis_conn):
        client.get("/api/categories")
        client.get("/api/categories")
        assert redis_conn.zscore("endpoint_stats", "/api/categories") == 2

    def test_non_api_path_not_counted(self, client, redis_conn):
        client.get("/health")
        assert redis_conn.zcard("endpoint_stats") == 0

    def test_daily_counter_incremented(self, client, redis_conn):
        from datetime import datetime

        client.get("/api/categories")
        key = f"req_count:{datetime.utcnow():%Y-%m-%d}"
        assert redis_conn.get(key) == "1"

    def test_daily_counter_expires(self, client, redis_conn):
        """Admin panel haftalik oynani o'qiydi — 8 kunlik TTL yetarli."""
        from datetime import datetime

        client.get("/api/categories")
        key = f"req_count:{datetime.utcnow():%Y-%m-%d}"
        assert 0 < redis_conn.ttl(key) <= 8 * 86400

    def test_live_request_is_published(self, client, redis_conn):
        pubsub = subscribe_to(redis_conn, "live_requests")
        client.get("/api/categories")
        messages = drain(pubsub)
        pubsub.close()
        assert messages, "live_requests kanaliga xabar chiqmadi"
        payload = json.loads(messages[0]["data"])
        assert payload["path"] == "/api/categories"
        assert payload["method"] == "GET"
        assert payload["status"] == 401

    def test_redis_failure_does_not_break_the_request(self, client):
        """
        Statistika yozish after_request da — Redis o'chgan bo'lsa ham
        foydalanuvchi javobini buzmasligi kerak.
        """
        import redis as redis_lib

        with patch("utils.cache.redis_client.zincrby",
                   side_effect=redis_lib.ConnectionError("down")):
            resp = client.get("/health")
        assert resp.status_code == 200

    def test_response_is_returned_unchanged(self, client):
        resp = client.get("/health")
        assert resp.get_json()["data"]["status"] == "up"


# ─── system_monitor ──────────────────────────────────────────────────────────

class _StopLoop(Exception):
    """time.sleep orqali cheksiz tsiklni to'xtatish uchun."""


class TestSystemMonitor:
    def _run_one_iteration(self, app_module, cpu, ram, redis_conn):
        vm = MagicMock()
        vm.percent = ram
        with patch("psutil.cpu_percent", return_value=cpu), \
             patch("psutil.virtual_memory", return_value=vm), \
             patch("app.time.sleep", side_effect=_StopLoop):
            with pytest.raises(_StopLoop):
                app_module.system_monitor()

    def test_publishes_metrics(self, app_module, redis_conn):
        pubsub = subscribe_to(redis_conn, "server_metrics")
        self._run_one_iteration(app_module, cpu=12.5, ram=40.0, redis_conn=redis_conn)
        messages = drain(pubsub)
        pubsub.close()
        assert messages, "server_metrics kanaliga xabar chiqmadi"
        payload = json.loads(messages[0]["data"])
        assert payload["cpu"] == 12.5
        assert payload["ram"] == 40.0
        assert "server" in payload and "time" in payload

    def test_no_alert_below_threshold(self, app_module, redis_conn):
        with patch("app.send_message") as mock_send:
            self._run_one_iteration(app_module, cpu=50.0, ram=50.0, redis_conn=redis_conn)
        mock_send.assert_not_called()

    def test_alerts_admins_when_cpu_critical(self, app_module, redis_conn):
        with patch("app.send_message") as mock_send:
            self._run_one_iteration(app_module, cpu=95.0, ram=10.0, redis_conn=redis_conn)
        assert mock_send.call_count == 2  # conftest ADMINS="111111,222222"
        assert "95.0" in mock_send.call_args[0][1]

    def test_alerts_admins_when_ram_critical(self, app_module, redis_conn):
        with patch("app.send_message") as mock_send:
            self._run_one_iteration(app_module, cpu=10.0, ram=99.0, redis_conn=redis_conn)
        assert mock_send.call_count == 2

    def test_admin_ids_are_ints(self, app_module, redis_conn):
        with patch("app.send_message") as mock_send:
            self._run_one_iteration(app_module, cpu=95.0, ram=10.0, redis_conn=redis_conn)
        assert all(isinstance(c[0][0], int) for c in mock_send.call_args_list)

    def test_no_admins_configured_sends_nothing(self, app_module, redis_conn):
        with patch("app.Config.ADMINS", ""), patch("app.send_message") as mock_send:
            self._run_one_iteration(app_module, cpu=95.0, ram=99.0, redis_conn=redis_conn)
        mock_send.assert_not_called()

    def test_redis_failure_does_not_kill_the_loop(self, app_module, redis_conn):
        """
        Monitor daemon thread — bitta xato uni o'ldirsa, metrikalar
        butunlay to'xtaydi va buni hech kim sezmaydi.
        """
        import redis as redis_lib

        vm = MagicMock()
        vm.percent = 10.0
        with patch("psutil.cpu_percent", return_value=10.0), \
             patch("psutil.virtual_memory", return_value=vm), \
             patch("utils.cache.redis_client.publish",
                   side_effect=redis_lib.ConnectionError("down")), \
             patch("app.time.sleep", side_effect=_StopLoop):
            with pytest.raises(_StopLoop):
                app_module.system_monitor()
            # Xato ushlanib, tsikl sleep ga yetib keldi — demak yiqilmadi
