"""
Kochatim Backend Test Suite — conftest.py
Barcha test qatlamlari uchun umumiy fixtures va setup.
"""
import hashlib
import hmac
import json
import os
import sys
import time
from datetime import datetime
from unittest.mock import MagicMock, patch

# ─── Backend modulni sys.path ga qo'shish ────────────────────────────────────
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# ─── Test uchun muhit o'zgaruvchilari (import OLDIN) ─────────────────────────
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test_kochatim")
os.environ.setdefault("API_KEY", "test-api-key-12345")
os.environ.setdefault("BOT_TOKEN", "123456789:TEST_BOT_TOKEN_ABCDEF1234")
os.environ.setdefault("TG_BOT_USERNAME", "test_kochatim_bot")
os.environ.setdefault("IMGBB_API_KEY", "test-imgbb-api-key")
os.environ.setdefault("FLASK_ENV", "testing")
os.environ.setdefault("OTP_TTL_SECONDS", "120")
os.environ.setdefault("SESSION_TTL_SECONDS", "2592000")
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173")
os.environ.setdefault("DB_POOL_MIN", "1")
os.environ.setdefault("DB_POOL_MAX", "5")

import pytest

# ─── Test konstantalari ───────────────────────────────────────────────────────
TEST_API_KEY = "test-api-key-12345"
TEST_BOT_TOKEN = "123456789:TEST_BOT_TOKEN_ABCDEF1234"
TEST_U_ID = 123456789
TEST_TOKEN = "valid-session-token-for-tests-xyz"
TEST_OTP_CODE = "123456"

NOW = datetime(2026, 6, 13, 12, 0, 0)


def get_test_token_hash() -> str:
    from utils.security import sha256_hex
    return sha256_hex(TEST_TOKEN)


def build_valid_init_data(bot_token: str, u_id: int = TEST_U_ID) -> str:
    """Telegram WebApp uchun haqiqiy HMAC imzoli initData yaratish."""
    user_obj = json.dumps({"id": u_id, "first_name": "Test", "username": "testuser"})
    pairs = {
        "user": user_obj,
        "auth_date": str(int(time.time())),
        "query_id": "test_query_id_abc",
    }
    data_check_string = "\n".join(f"{k}={pairs[k]}" for k in sorted(pairs.keys()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    h = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    pairs["hash"] = h
    return "&".join(f"{k}={v}" for k, v in pairs.items())


# ─── Fake DB rows ─────────────────────────────────────────────────────────────
FAKE_USER = {
    "u_id": TEST_U_ID,
    "u_name": "Test Foydalanuvchi",
    "u_phone": "+998901234567",
    "u_username": "testuser",
    "u_age": 25,
    "u_photo": None,
    "added_at": NOW,
    "updated_at": None,
}

FAKE_CATEGORY = {
    "c_id": 1,
    "c_name": "Mevali daraxtlar",
    "u_id": TEST_U_ID,
    "added_at": NOW,
    "updated_at": None,
}

FAKE_TYPE = {
    "t_id": 10,
    "u_id": TEST_U_ID,
    "c_id": 1,
    "t_name": "Olma",
    "deff": "Yaxshi nav",
    "i_url": None,
    "added_at": NOW,
    "updated_at": None,
}

FAKE_SEEDLING_ROW = {
    "s_id": 1,
    "t_id": 10,
    "t_name": "Olma",
    "quality_1": 100,
    "quality_2": 50,
    "quality_3": 25,
    "updated_at": NOW,
    "added_at": NOW,
}

FAKE_SALE = {
    "sale_id": 1,
    "u_id": TEST_U_ID,
    "c_id": 1,
    "t_id": 10,
    "q1_sold": 5,
    "q2_sold": 3,
    "q3_sold": 1,
    "price": 150000,
    "sold_at": NOW,
    "c_name": "Mevali daraxtlar",
    "t_name": "Olma",
}

FAKE_SESSION_DB_ROW = {
    "session_id": 1,
    "device_name": "Chrome macOS",
    "city": "Toshkent",
    "ip_address": "127.0.0.1",
    "created_at": NOW,
    "token_hash": "somehash",
}

FAKE_PARTNER = {
    "u_id": 987654321,
    "u_name": "Hamkor Foydalanuvchi",
    "u_phone": "+998901111111",
    "u_username": "partneruser",
    "u_age": 30,
    "u_photo": None,
    "created_at": NOW,
}

FAKE_LOGIN_CODE = {
    "id": 1,
    "u_id": TEST_U_ID,
    "expires_at": datetime(2099, 1, 1),
    "used_at": None,
    "code_hash": hashlib.sha256(TEST_OTP_CODE.encode()).hexdigest(),
}

FAKE_INVITE = {
    "token": "test-invite-token-xyz",
    "inviter_u_id": TEST_U_ID,
    "expires_at": datetime(2099, 1, 1),
    "used_at": None,
}


# ─── Flask app fixture ────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def app():
    """
    Flask test app — real DB ulanishisiz.
    extensions.init_pool va db_init.init_db mock qilinadi.
    """
    with patch("extensions.init_pool"), patch("db_init.init_db"):
        from app import create_app
        application = create_app()
        application.config["TESTING"] = True
        application.config["WTF_CSRF_ENABLED"] = False
    return application


@pytest.fixture
def client(app):
    return app.test_client()


# ─── Autouse: har test oldidan keshni tozalash ───────────────────────────────

@pytest.fixture(autouse=True)
def clear_in_memory_cache():
    """Har test oldidan utils.cache._store tozalanadi."""
    import utils.cache as cache_module
    cache_module._store.clear()
    yield
    cache_module._store.clear()


# ─── Header fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def api_key_headers():
    return {"X-API-KEY": TEST_API_KEY, "Content-Type": "application/json"}


@pytest.fixture
def session_headers():
    return {
        "Authorization": f"Bearer {TEST_TOKEN}",
        "Content-Type": "application/json",
    }


@pytest.fixture
def no_auth_headers():
    return {"Content-Type": "application/json"}


# ─── Session middleware mock ──────────────────────────────────────────────────

@pytest.fixture
def mock_session():
    """
    require_session middleware ni o'tkazadi.
    get_cache dan to'g'ridan-to'g'ri u_id qaytaradi (cache hit).
    """
    with patch("middleware.require_session.get_cache", return_value=TEST_U_ID):
        yield


@pytest.fixture
def mock_session_miss():
    """
    Cache miss — DB ga so'rov ketadi.
    DB dan session topiladi.
    """
    session_row = {"u_id": TEST_U_ID}
    with patch("middleware.require_session.get_cache", return_value=None), \
         patch("middleware.require_session.fetch_one", return_value=session_row), \
         patch("middleware.require_session.set_cache"):
        yield
