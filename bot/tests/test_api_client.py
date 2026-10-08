"""
Tests — bot/api_client.py

Bot backend bilan faqat shu modul orqali gaplashadi. Shartnoma:

- har so'rovda `X-API-KEY` ketadi (aks holda backend 401 beradi);
- backend `{"ok": false, ...}` qaytarsa HTTP 200 bo'lsa ham
  `BackendAPIError` ko'tariladi — javobning `ok` maydoni haqiqiy
  muvaffaqiyat belgisi, status kod emas;
- muvaffaqiyatda faqat `data` qismi qaytariladi.
"""
import pytest

from conftest import TEST_API_KEY, TEST_API_URL, TEST_U_ID

pytestmark = pytest.mark.asyncio


def ok_body(data):
    return {"ok": True, "data": data}


def fail_body(message="nope", code=None):
    err = {"message": message}
    if code:
        err["code"] = code
    return {"ok": False, "error": err}


# ─── get_session ──────────────────────────────────────────────────────────────

class TestGetSession:
    async def test_returns_a_session(self, api_client):
        session = api_client.get_session()
        try:
            assert session is not None
        finally:
            await session.close()

    async def test_reuses_the_same_session(self, api_client):
        first = api_client.get_session()
        try:
            assert api_client.get_session() is first
        finally:
            await first.close()

    async def test_creates_a_new_session_when_closed(self, api_client):
        """Yopilgan sessiya qayta ishlatilsa aiohttp xato beradi."""
        first = api_client.get_session()
        await first.close()
        second = api_client.get_session()
        try:
            assert second is not first
        finally:
            await second.close()


# ─── _request — sozlama tekshiruvi ───────────────────────────────────────────

class TestRequestConfiguration:
    async def test_missing_api_url_raises(self, api_client):
        api_client.API_URL = ""
        with pytest.raises(api_client.BackendAPIError, match="not configured"):
            await api_client._request("GET", "/api/me")

    async def test_missing_api_key_raises(self, api_client):
        api_client.API_KEY = ""
        with pytest.raises(api_client.BackendAPIError, match="not configured"):
            await api_client._request("GET", "/api/me")

    async def test_no_request_is_sent_when_unconfigured(self, api_client, backend):
        api_client.API_KEY = ""
        with pytest.raises(api_client.BackendAPIError):
            await api_client._request("GET", "/api/me")
        assert backend.calls == []


# ─── _request — sarlavhalar, URL, metod ──────────────────────────────────────

class TestRequestWiring:
    async def test_sends_api_key_header(self, api_client, backend):
        backend.respond(payload=ok_body({"u_id": 1}))
        await api_client.get_user(1)
        assert backend.last["headers"]["X-API-KEY"] == TEST_API_KEY

    async def test_sends_json_content_type(self, api_client, backend):
        backend.respond(payload=ok_body({"u_id": 1}))
        await api_client.get_user(1)
        assert backend.last["headers"]["Content-Type"] == "application/json"

    async def test_builds_url_from_api_url_and_path(self, api_client, backend):
        backend.respond(payload=ok_body({}))
        await api_client.get_user(42)
        assert backend.last["url"] == f"{TEST_API_URL}/api/users/42"

    async def test_trailing_slash_is_stripped_from_api_url(self, api_client, backend):
        """URL ikki slash bilan qurilsa backend 404 beradi."""
        api_client.API_URL = "http://backend:8000/".rstrip("/")
        backend.respond(payload=ok_body({}))
        await api_client.get_user(1)
        assert "//api" not in backend.last["url"].replace("http://", "")

    async def test_uses_the_requested_method(self, api_client, backend):
        backend.respond(payload=ok_body({}))
        await api_client.ensure_user(TEST_U_ID, "Ali", "ali")
        assert backend.last["method"] == "POST"

    async def test_get_sends_no_body(self, api_client, backend):
        backend.respond(payload=ok_body({}))
        await api_client.get_user(1)
        assert backend.last["json"] is None


# ─── _request — xatolik yo'llari ─────────────────────────────────────────────

class TestRequestErrors:
    async def test_http_error_status_raises(self, api_client, backend):
        backend.respond(status=500, payload=fail_body("server error"))
        with pytest.raises(api_client.BackendAPIError):
            await api_client.get_user(1)

    async def test_ok_false_raises_even_on_http_200(self, api_client, backend):
        """
        Backend HTTP 200 bilan `ok: false` qaytarishi mumkin — faqat
        status kodga ishonib bo'lmaydi.
        """
        backend.respond(status=200, payload=fail_body("User not found", code="NOT_FOUND"))
        with pytest.raises(api_client.BackendAPIError):
            await api_client.get_user(1)

    async def test_error_payload_is_attached_to_the_exception(self, api_client, backend):
        backend.respond(status=404, payload=fail_body("User not found", code="NOT_FOUND"))
        with pytest.raises(api_client.BackendAPIError) as exc:
            await api_client.get_user(1)
        assert "NOT_FOUND" in str(exc.value)

    async def test_unparseable_body_propagates(self, api_client, backend):
        """Nginx 502 HTML sahifasi qaytarsa — xato yashirilmasligi kerak."""
        backend.respond(status=502, json_error=ValueError("not json"))
        with pytest.raises(ValueError):
            await api_client.get_user(1)

    async def test_backend_api_error_is_an_exception(self, api_client):
        assert issubclass(api_client.BackendAPIError, Exception)


# ─── ensure_user ──────────────────────────────────────────────────────────────

class TestEnsureUser:
    async def test_returns_data_section_only(self, api_client, backend):
        backend.respond(payload=ok_body({"u_id": TEST_U_ID, "u_name": "Ali"}))
        result = await api_client.ensure_user(TEST_U_ID, "Ali", "ali")
        assert result == {"u_id": TEST_U_ID, "u_name": "Ali"}

    async def test_posts_to_users_ensure(self, api_client, backend):
        backend.respond(payload=ok_body({}))
        await api_client.ensure_user(TEST_U_ID, "Ali", "ali")
        assert backend.last["url"].endswith("/api/users/ensure")

    async def test_sends_all_profile_fields(self, api_client, backend):
        backend.respond(payload=ok_body({}))
        await api_client.ensure_user(
            TEST_U_ID, "Ali", "ali",
            u_phone="+998901234567", u_age=25, u_photo="AgACAgIAAxk",
        )
        body = backend.last["json"]
        assert body["u_id"] == TEST_U_ID
        assert body["u_name"] == "Ali"
        assert body["u_username"] == "ali"
        assert body["u_phone"] == "+998901234567"
        assert body["u_age"] == 25
        assert body["u_photo"] == "AgACAgIAAxk"

    async def test_optional_fields_default_to_none(self, api_client, backend):
        """
        Backend UPSERT da COALESCE ishlatadi — None yuborish mavjud
        qiymatni saqlab qoladi, bo'sh satr esa uni o'chirib yuborardi.
        """
        backend.respond(payload=ok_body({}))
        await api_client.ensure_user(TEST_U_ID, "Ali", "ali")
        body = backend.last["json"]
        assert body["u_phone"] is None
        assert body["u_age"] is None
        assert body["u_photo"] is None

    async def test_backend_failure_raises(self, api_client, backend):
        backend.respond(status=400, payload=fail_body("u_id(int) required"))
        with pytest.raises(api_client.BackendAPIError):
            await api_client.ensure_user(None, "Ali", "ali")


# ─── get_user ─────────────────────────────────────────────────────────────────

class TestGetUser:
    async def test_returns_user(self, api_client, backend):
        backend.respond(payload=ok_body({"u_id": TEST_U_ID}))
        assert await api_client.get_user(TEST_U_ID) == {"u_id": TEST_U_ID}

    async def test_puts_u_id_in_the_path(self, api_client, backend):
        backend.respond(payload=ok_body({}))
        await api_client.get_user(TEST_U_ID)
        assert backend.last["url"].endswith(f"/api/users/{TEST_U_ID}")

    async def test_not_found_raises(self, api_client, backend):
        backend.respond(status=404, payload=fail_body("User not found", code="NOT_FOUND"))
        with pytest.raises(api_client.BackendAPIError):
            await api_client.get_user(999)


# ─── Hamkorlik endpointlari ───────────────────────────────────────────────────

class TestPartners:
    async def test_accept_sends_token_and_u_id(self, api_client, backend):
        backend.respond(payload=ok_body({"accepted": True}))
        result = await api_client.partners_accept("tok-123", TEST_U_ID)
        assert backend.last["json"] == {"token": "tok-123", "u_id": TEST_U_ID}
        assert result == {"accepted": True}

    async def test_accept_coerces_u_id_to_int(self, api_client, backend):
        """Backend `isinstance(u_id, int)` tekshiradi — satr 400 beradi."""
        backend.respond(payload=ok_body({}))
        await api_client.partners_accept("tok", "123456789")
        assert backend.last["json"]["u_id"] == 123456789

    async def test_expired_invite_raises(self, api_client, backend):
        backend.respond(status=400, payload=fail_body("Invite expired",
                                                      code="INVITE_EXPIRED"))
        with pytest.raises(api_client.BackendAPIError, match="INVITE_EXPIRED"):
            await api_client.partners_accept("old-token", TEST_U_ID)

    async def test_already_partners_is_a_success_response(self, api_client, backend):
        """Backend bu holatni ok: true bilan qaytaradi — xato emas."""
        backend.respond(payload=ok_body({"accepted": False, "already_partners": True}))
        result = await api_client.partners_accept("tok", TEST_U_ID)
        assert result["already_partners"] is True

    async def test_decline_sends_token_and_u_id(self, api_client, backend):
        backend.respond(payload=ok_body({"declined": True}))
        result = await api_client.partners_decline("tok-123", TEST_U_ID)
        assert backend.last["json"] == {"token": "tok-123", "u_id": TEST_U_ID}
        assert result == {"declined": True}

    async def test_decline_posts_to_decline_route(self, api_client, backend):
        backend.respond(payload=ok_body({}))
        await api_client.partners_decline("tok", TEST_U_ID)
        assert backend.last["url"].endswith("/api/partners/decline")

    async def test_get_partners_returns_list(self, api_client, backend):
        rows = [{"u_id": 1, "u_name": "A"}, {"u_id": 2, "u_name": "B"}]
        backend.respond(payload=ok_body(rows))
        assert await api_client.get_partners(TEST_U_ID) == rows

    async def test_get_partners_empty_list(self, api_client, backend):
        backend.respond(payload=ok_body([]))
        assert await api_client.get_partners(TEST_U_ID) == []

    async def test_get_partners_uses_nested_path(self, api_client, backend):
        backend.respond(payload=ok_body([]))
        await api_client.get_partners(TEST_U_ID)
        assert backend.last["url"].endswith(f"/api/users/{TEST_U_ID}/partners")


# ─── request_login_code ───────────────────────────────────────────────────────

class TestRequestLoginCode:
    async def test_returns_code_and_ttl(self, api_client, backend):
        backend.respond(payload=ok_body({"code": "123456", "expires_in": 120}))
        result = await api_client.request_login_code(TEST_U_ID, "Ali", "ali")
        assert result == {"code": "123456", "expires_in": 120}

    async def test_posts_to_auth_route_not_api(self, api_client, backend):
        backend.respond(payload=ok_body({}))
        await api_client.request_login_code(TEST_U_ID, "Ali", "ali")
        assert backend.last["url"].endswith("/auth/request-code")

    async def test_sends_profile_fields(self, api_client, backend):
        backend.respond(payload=ok_body({}))
        await api_client.request_login_code(
            TEST_U_ID, "Ali", "ali", u_phone="+998901234567", u_age=30
        )
        body = backend.last["json"]
        assert body["u_id"] == TEST_U_ID
        assert body["u_phone"] == "+998901234567"
        assert body["u_age"] == 30

    async def test_sends_api_key(self, api_client, backend):
        """/auth/request-code backend'da require_api_key bilan himoyalangan."""
        backend.respond(payload=ok_body({}))
        await api_client.request_login_code(TEST_U_ID, "Ali", "ali")
        assert backend.last["headers"]["X-API-KEY"] == TEST_API_KEY

    async def test_backend_down_raises(self, api_client, backend):
        backend.respond(status=503, payload=fail_body("unavailable"))
        with pytest.raises(api_client.BackendAPIError):
            await api_client.request_login_code(TEST_U_ID, "Ali", "ali")

    async def test_otp_code_is_not_logged_in_the_exception(self, api_client, backend):
        """Xatolik matnida OTP kodi bo'lmasligi kerak."""
        backend.respond(status=400, payload=fail_body("u_id(int) required"))
        with pytest.raises(api_client.BackendAPIError) as exc:
            await api_client.request_login_code(TEST_U_ID, "Ali", "ali")
        assert "123456" not in str(exc.value)
