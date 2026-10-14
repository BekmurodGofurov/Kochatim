"""
Integration tests — middleware/client_gate.py

The backend answers only the bot (X-API-KEY) and the web client
(X-Client-Key). These tests walk every route the app registers, so a route
added later without thinking about access fails here rather than shipping open.
"""
from unittest.mock import patch

import pytest
from werkzeug.routing import IntegerConverter

from conftest import TEST_API_KEY, TEST_WEB_KEY

# Routes with no auth decorator, and why each is allowed to be one.
# Adding to this set is a security decision: write the reason down.
PUBLIC_ENDPOINTS = {
    "health":                          "uptime / Docker probes cannot send a key",
    "auth.verify_code":                "login: redeems a one-time code (needs the web key)",
    "auth.telegram_webapp_login":      "login: verifies Telegram's HMAC (needs the web key)",
    "api.search_gardeners":            "directory: names only (needs the web key)",
    "api.dashboard_user":              "profile page: name only unless the viewer is a partner",
    "api.proxy_telegram_image":        "<img src>: takes the web key as ?k=",
    "public.public_categories":        "landing page category list, no identifiers",
}


def _routes(app):
    """(rule, endpoint, view, method) for every real route, static files excluded."""
    for rule in app.url_map.iter_rules():
        if rule.endpoint == "static":
            continue
        for method in sorted(rule.methods - {"HEAD", "OPTIONS"}):
            yield rule, rule.endpoint, app.view_functions[rule.endpoint], method


def _url(app, rule):
    adapter = app.url_map.bind("localhost")
    values = {
        arg: 1 if isinstance(rule._converters[arg], IntegerConverter) else "x"
        for arg in rule.arguments
    }
    return adapter.build(rule.endpoint, values)


def _all(app):
    return [(r, ep, v, m) for r, ep, v, m in _routes(app)]


def _id(param):
    return f"{param[3]} {param[0].rule}"


@pytest.fixture(scope="module")
def routes(app):
    return _all(app)


# ─── Nothing answers without a key ─────────────────────────────────────────────

class TestNoKeyNoAnswer:
    def test_every_route_rejects_a_request_with_no_key(self, app, client, routes):
        failures = []
        for rule, endpoint, _, method in routes:
            if endpoint == "health":
                continue
            resp = client.open(_url(app, rule), method=method)
            if resp.status_code != 401:
                failures.append(f"{method} {rule.rule} -> {resp.status_code}")
        assert not failures, "reachable without a key:\n" + "\n".join(failures)

    def test_every_route_returns_the_same_bare_401(self, app, client, routes):
        bodies = set()
        for rule, endpoint, _, method in routes:
            if endpoint == "health":
                continue
            resp = client.open(_url(app, rule), method=method)
            bodies.add(resp.get_data(as_text=True))
        assert len(bodies) == 1  # no route can be told apart from another

    def test_a_made_up_path_is_indistinguishable_from_a_real_one(self, client):
        real = client.get("/api/me")
        fake = client.get("/api/definitely/not/a/route")
        assert real.status_code == fake.status_code == 401
        assert real.get_json() == fake.get_json()

    def test_the_401_does_not_say_which_key_was_expected(self, client):
        body = client.get("/api/me").get_data(as_text=True).lower()
        for word in ("x-api-key", "x-client-key", "web", "bot"):
            assert word not in body

    def test_the_gate_runs_before_the_handler(self, client):
        with patch("api.users.fetch_all") as fa:
            client.get("/api/gardeners")
        fa.assert_not_called()

    def test_an_app_built_by_the_factory_is_gated_too(self, factory_app):
        """The gate lives in create_app(), not only in the module-level app."""
        resp = factory_app.test_client().get("/api/gardeners")
        assert resp.status_code == 401


class TestOpenPaths:
    def test_health_needs_no_key(self, client):
        assert client.get("/health").status_code == 200

    def test_preflight_needs_no_key(self, client):
        resp = client.open("/api/me", method="OPTIONS", headers={"Origin": "http://localhost:5173"})
        assert resp.status_code == 204

    def test_preflight_does_not_open_the_route_itself(self, client):
        client.open("/api/me", method="OPTIONS")
        assert client.get("/api/me").status_code == 401

    def test_health_with_a_trailing_junk_path_is_not_open(self, client):
        assert client.get("/health/anything").status_code == 401
        assert client.get("/healthz").status_code == 401


# ─── The two identities stay apart ─────────────────────────────────────────────

class TestPrivilegeSeparation:
    def test_every_route_is_either_decorated_or_explicitly_public(self, routes):
        """A new route with no decorator and no entry above fails this test."""
        undeclared = [
            f"{rule.rule} ({endpoint})"
            for rule, endpoint, view, _ in routes
            if getattr(view, "auth_kind", None) is None and endpoint not in PUBLIC_ENDPOINTS
        ]
        assert not undeclared, "public by accident? " + ", ".join(sorted(set(undeclared)))

    def test_public_allowlist_has_no_stale_entries(self, routes):
        known = {endpoint for _, endpoint, _, _ in routes}
        assert set(PUBLIC_ENDPOINTS) <= known

    def test_the_web_key_never_opens_a_bot_route(self, app, client, routes):
        """Bot routes take u_id from the caller. The web key is public, so it must not work there."""
        opened = []
        for rule, endpoint, view, method in routes:
            if getattr(view, "auth_kind", None) != "api_key":
                continue
            resp = client.open(_url(app, rule), method=method, headers={"X-Client-Key": TEST_WEB_KEY})
            if resp.status_code != 401:
                opened.append(f"{method} {rule.rule} -> {resp.status_code}")
        assert not opened, "web key reached bot routes:\n" + "\n".join(opened)

    def test_the_web_key_in_the_bot_header_is_not_the_bot_key(self, app, client, routes):
        for rule, _, view, method in routes:
            if getattr(view, "auth_kind", None) == "api_key":
                resp = client.open(_url(app, rule), method=method, headers={"X-API-KEY": TEST_WEB_KEY})
                assert resp.status_code == 401, rule.rule

    def test_the_bot_key_in_the_web_header_is_not_the_web_key(self, app, client, routes):
        for rule, endpoint, _, method in routes:
            if endpoint == "health":
                continue
            resp = client.open(_url(app, rule), method=method, headers={"X-Client-Key": TEST_API_KEY})
            assert resp.status_code == 401, rule.rule

    def test_the_bot_key_never_opens_a_session_route(self, app, client, routes):
        opened = []
        for rule, endpoint, view, method in routes:
            if getattr(view, "auth_kind", None) != "session":
                continue
            resp = client.open(_url(app, rule), method=method, headers={"X-API-KEY": TEST_API_KEY})
            # The gate lets the bot in; require_session must still refuse it.
            if resp.status_code != 401:
                opened.append(f"{method} {rule.rule} -> {resp.status_code}")
        assert not opened, "bot key reached session routes:\n" + "\n".join(opened)

    def test_the_bot_key_reaches_bot_routes_past_the_gate(self, app, client, routes):
        for rule, endpoint, view, method in routes:
            if getattr(view, "auth_kind", None) != "api_key":
                continue
            resp = client.open(_url(app, rule), method=method, headers={"X-API-KEY": TEST_API_KEY})
            assert resp.status_code != 401, f"{method} {rule.rule}"

    def test_the_web_key_reaches_public_routes_past_the_gate(self, app, client, routes):
        for rule, endpoint, view, method in routes:
            if endpoint not in PUBLIC_ENDPOINTS or endpoint == "health":
                continue
            resp = client.open(_url(app, rule), method=method, headers={"X-Client-Key": TEST_WEB_KEY})
            assert resp.status_code != 401, f"{method} {rule.rule}"


# ─── What counts as a key ───────────────────────────────────────────────────────

class TestKeyHandling:
    URL = "/api/gardeners"

    @pytest.mark.parametrize("headers", [
        {"X-Client-Key": ""},
        {"X-Client-Key": "   "},
        {"X-Client-Key": "wrong"},
        {"X-Client-Key": TEST_WEB_KEY[:-1]},
        {"X-Client-Key": TEST_WEB_KEY + "x"},
        {"X-Client-Key": TEST_WEB_KEY.upper()},
        {"X-Client-Key": f"Bearer {TEST_WEB_KEY}"},
        {"X-API-KEY": ""},
        {"X-API-KEY": TEST_API_KEY.upper()},
        {"Authorization": f"Bearer {TEST_WEB_KEY}"},
        {"Cookie": f"X-Client-Key={TEST_WEB_KEY}"},
        {"x-client-key-extra": TEST_WEB_KEY},
    ])
    def test_wrong_or_misplaced_keys_are_rejected(self, client, headers):
        assert client.get(self.URL, headers=headers).status_code == 401

    def test_surrounding_whitespace_is_tolerated(self, client):
        with patch("api.users.fetch_all", return_value=[]):
            resp = client.get(self.URL, headers={"X-Client-Key": f"  {TEST_WEB_KEY}  "})
        assert resp.status_code == 200

    def test_header_names_are_case_insensitive_as_http_requires(self, client):
        with patch("api.users.fetch_all", return_value=[]):
            resp = client.get(self.URL, headers={"x-client-key": TEST_WEB_KEY})
        assert resp.status_code == 200

    def test_key_in_the_query_string_is_ignored_on_ordinary_routes(self, client):
        assert client.get(f"{self.URL}?k={TEST_WEB_KEY}").status_code == 401
        assert client.get(f"{self.URL}?X-Client-Key={TEST_WEB_KEY}").status_code == 401

    def test_key_in_the_body_is_ignored(self, client):
        resp = client.post("/auth/verify-code", json={"X-Client-Key": TEST_WEB_KEY, "code": "123456"})
        assert resp.status_code == 401

    def test_key_in_the_query_is_accepted_only_for_the_image_route_and_only_on_get(self, client):
        with patch("api.images.requests.get", side_effect=RuntimeError("stop")):
            assert client.get(f"/api/img/abc?k={TEST_WEB_KEY}").status_code != 401
        assert client.get("/api/img/abc?k=wrong").status_code == 401
        assert client.get("/api/img/abc").status_code == 401
        assert client.post(f"/api/img/abc?k={TEST_WEB_KEY}").status_code == 401
        assert client.get(f"/api/img/by-type?t_id=1&k={TEST_WEB_KEY}").status_code == 401

    def test_the_bot_key_in_the_image_query_is_not_accepted(self, client):
        assert client.get(f"/api/img/abc?k={TEST_API_KEY}").status_code == 401

    def test_keys_are_compared_in_constant_time(self, client):
        with patch("middleware.client_gate.safe_equal", return_value=False) as cmp:
            client.get(self.URL, headers={"X-Client-Key": "x", "X-API-KEY": "y"})
        assert cmp.called

    @pytest.mark.parametrize("name", ["API_KEY", "WEB_CLIENT_KEY"])
    def test_an_unset_key_never_matches_a_blank_header(self, client, name):
        """If the server forgot to configure a key, an empty header must not become a master key."""
        header = {"API_KEY": "X-API-KEY", "WEB_CLIENT_KEY": "X-Client-Key"}[name]
        with patch(f"middleware.client_gate.Config.{name}", ""):
            assert client.get(self.URL, headers={header: ""}).status_code == 401
            assert client.get(self.URL, headers={header: " "}).status_code == 401

    def test_identity_is_set_for_the_handler(self, client):
        from flask import g
        seen = []

        def spy(*a, **k):
            seen.append(g.client)
            return []
        with patch("api.users.fetch_all", side_effect=spy):
            client.get(self.URL, headers={"X-Client-Key": TEST_WEB_KEY})
            client.get(self.URL, headers={"X-API-KEY": TEST_API_KEY})
            client.get(self.URL, headers={"X-API-KEY": TEST_API_KEY, "X-Client-Key": TEST_WEB_KEY})
        assert seen == ["web", "bot", "bot"]  # the bot key wins if both are valid

    def test_redis_outage_does_not_affect_the_gate(self, client):
        import redis as redis_lib
        with patch("utils.cache.redis_client.get", side_effect=redis_lib.ConnectionError("down")), \
             patch("api.users.fetch_all", return_value=[]):
            assert client.get(self.URL, headers={"X-Client-Key": TEST_WEB_KEY}).status_code == 200
            assert client.get(self.URL).status_code == 401
