"""
Kochatim backend test suite — shared fixtures.

Import order in this file is load-bearing. Three things must happen before
``backend/app.py`` is imported, and all three are done at module level rather
than in fixtures, because fixtures run too late:

1. Env vars are seeded. ``config.Config`` reads ``os.getenv`` at class-body
   evaluation, so a missing var is baked in permanently at import time.
2. ``utils.cache.redis_client`` is swapped for a fakeredis instance. The real
   client is built at module import, and ``db_init`` binds it by value
   (``from utils.cache import redis_client``).
3. ``init_pool``, ``init_db`` and the monitor thread are patched. ``app.py``
   calls ``create_app()`` at module level, which opens a real Postgres pool,
   and it starts a psutil polling thread that never stops.

See `skills/testing/SKILL.md` for the reasoning behind each.
"""
import hashlib
import hmac
import json
import os
import sys
import threading
import time
from datetime import datetime
from unittest.mock import MagicMock, patch

# ─── 1. Backend modulini sys.path ga qo'shish ────────────────────────────────
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# ─── 2. Muhit o'zgaruvchilari (har qanday backend import'dan OLDIN) ──────────
# Config klass tanasi import vaqtida os.getenv o'qiydi — fixture juda kech.
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test_kochatim")
os.environ.setdefault("API_KEY", "test-api-key-12345")
os.environ.setdefault("BOT_TOKEN", "123456789:TEST_BOT_TOKEN_ABCDEF1234")
os.environ.setdefault("TG_BOT_USERNAME", "test_kochatim_bot")
os.environ.setdefault("IMGBB_API_KEY", "test-imgbb-api-key")
os.environ.setdefault("ADMINS", "111111,222222")
os.environ.setdefault("FLASK_ENV", "testing")
os.environ.setdefault("OTP_TTL_SECONDS", "120")
os.environ.setdefault("SESSION_TTL_SECONDS", "2592000")
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173")
os.environ.setdefault("DB_POOL_MIN", "1")
os.environ.setdefault("DB_POOL_MAX", "5")
os.environ.setdefault("REDIS_HOST", "127.0.0.1")
os.environ.setdefault("REDIS_PORT", "6379")

import pytest

# ─── 3. Fake Redis — utils.cache ning global clientini almashtirish ──────────
# utils/cache.py redis_client ni import vaqtida yaratadi. Haqiqiy serverga
# ulanmaydi (lazy), lekin birinchi buyruqda ConnectionError beradi. fakeredis
# bir xil API ni to'liq xotirada beradi — shuning uchun kesh kodi mock
# qilinmaydi, balki haqiqatda ishlatiladi.
import fakeredis

fake_redis = fakeredis.FakeRedis(decode_responses=True)

import utils.cache as _cache_module

_cache_module.redis_client = fake_redis

# db_init redis_client ni qiymat bo'yicha bog'laydi — uni ham almashtiramiz.
import db_init as _db_init_module

_db_init_module.redis_client = fake_redis


# ─── 4. Flask app ni xavfsiz import qilish ───────────────────────────────────
# app.py modul darajasida create_app() chaqiradi (init_pool + init_db) va
# system_monitor thread ini ishga tushiradi. Uchalasini import davomida
# to'xtatib turamiz.
def _import_app_module():
    with patch("extensions.init_pool"), \
         patch("db_init.init_db"), \
         patch.object(threading.Thread, "start", lambda self: None):
        import app as app_module
        return app_module


_app_module = _import_app_module()


# ─── Test konstantalari ───────────────────────────────────────────────────────
TEST_API_KEY = "test-api-key-12345"
TEST_BOT_TOKEN = "123456789:TEST_BOT_TOKEN_ABCDEF1234"
TEST_U_ID = 123456789
TEST_PARTNER_U_ID = 987654321
TEST_TOKEN = "valid-session-token-for-tests-xyz"
TEST_OTP_CODE = "123456"

NOW = datetime(2026, 6, 13, 12, 0, 0)
FAR_FUTURE = datetime(2099, 1, 1)
FAR_PAST = datetime(2000, 1, 1)


def get_test_token_hash() -> str:
    from utils.security import sha256_hex

    return sha256_hex(TEST_TOKEN)


def build_valid_init_data(bot_token: str, u_id: int = TEST_U_ID, **extra) -> str:
    """Telegram WebApp uchun haqiqiy HMAC imzoli initData yaratadi."""
    user_obj = json.dumps({"id": u_id, "first_name": "Test", "username": "testuser"})
    pairs = {
        "user": user_obj,
        "auth_date": str(int(time.time())),
        "query_id": "test_query_id_abc",
    }
    pairs.update(extra)
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
    "token_hash": get_test_token_hash(),
}

FAKE_PARTNER = {
    "u_id": TEST_PARTNER_U_ID,
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
    "expires_at": FAR_FUTURE,
    "used_at": None,
    "code_hash": hashlib.sha256(TEST_OTP_CODE.encode()).hexdigest(),
}

FAKE_INVITE = {
    "token": "test-invite-token-xyz",
    "inviter_u_id": TEST_U_ID,
    "expires_at": FAR_FUTURE,
    "used_at": None,
}


# ─── Flask app fixture ────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def app():
    """
    Flask app — `backend/app.py` ning modul darajasidagi nusxasi.

    MUHIM: `create_app()` ni qayta chaqirmaydi. CORS ishlovchilari
    (`_cors_preflight`, `_add_cors_headers`) va so'rov statistikasi
    (`_record_endpoint_stats`) `create_app()` ICHIDA emas, modul
    darajasida `@app.before_request` / `@app.after_request` dekoratori
    bilan ro'yxatga olingan. Shuning uchun `create_app()` dan qaytgan
    yangi app'da CORS ham, statistika ham YO'Q.

    Production gunicorn `app:app` ni, ya'ni aynan shu nusxani ishlatadi —
    test ham shuni ishlatishi kerak, aks holda CORS siyosati hech qachon
    tekshirilmaydi.
    """
    application = _app_module.app
    application.config["TESTING"] = True
    application.config["WTF_CSRF_ENABLED"] = False
    return application


@pytest.fixture
def factory_app():
    """`create_app()` dan qaytgan yangi app — fabrikani o'zini testlash uchun."""
    with patch("extensions.init_pool"), patch("db_init.init_db"):
        application = _app_module.create_app()
        application.config["TESTING"] = True
    return application


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def app_module():
    """backend/app.py moduli — CORS/health/stats helperlarini testlash uchun."""
    return _app_module


# ─── Autouse: har test oldidan Redis ni tozalash ─────────────────────────────

@pytest.fixture(autouse=True)
def clear_redis():
    """
    Har test izolyatsiyada ishlashi uchun fake Redis tozalanadi.

    Oldin bu fixture `utils.cache._store` lug'atini tozalagan edi. Kesh
    Redis'ga o'tganda `_store` yo'qoldi va butun to'plam (336 test)
    AttributeError bilan yiqildi — shuning uchun flushall ishlatiladi.
    """
    fake_redis.flushall()
    yield
    fake_redis.flushall()


@pytest.fixture
def redis_conn():
    """Fake Redis instance — kesh holatini to'g'ridan-to'g'ri tekshirish uchun."""
    return fake_redis


# ─── Autouse: fon thread'larini test ichida ushlab turish ────────────────────

class _InlineExecutor:
    """
    submit() ni darhol, shu thread'da bajaradi.

    `auth/user_id_login.py` sessiya yozishni ThreadPoolExecutor ga topshiradi
    va javobni kutmasdan qaytaradi. Natijada `with patch(...)` bloki fon
    vazifasi ishga tushishidan oldin yopiladi — mock yo'qoladi va thread
    HAQIQIY Postgres ga ulanishga harakat qiladi. Test to'plami shuning uchun
    "Background session insertion failed: ... role 'test' does not exist"
    deb log yozardi.

    Inline executor patch amal qilib turganda ishlaydi, shuning uchun fon
    vazifasi ham mock'langan DB ni ko'radi va testlar deterministik bo'ladi.
    """

    def submit(self, fn, *args, **kwargs):
        future = MagicMock()
        try:
            future.result.return_value = fn(*args, **kwargs)
        except Exception as exc:  # fon vazifasi o'zi ushlab qoladigan xato
            future.result.side_effect = exc
        return future


@pytest.fixture(autouse=True)
def inline_background_executor():
    """
    Fon vazifalari test ichida, mock'lar amal qilganda bajariladi.

    Modul `sys.modules` dan olinadi, `import auth.user_id_login` orqali emas:
    `auth/__init__.py` da `from auth.user_id_login import *` bor, u esa
    paket nomssohasida `user_id_login` nomini FUNKSIYA bilan almashtiradi.
    Shuning uchun `auth.user_id_login` atributi modulga emas, funksiyaga
    ishora qiladi va `patch.object` "does not have the attribute 'executor'"
    deb yiqiladi.
    """
    _uidl = sys.modules["auth.user_id_login"]

    with patch.object(_uidl, "executor", _InlineExecutor()):
        yield


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


# ─── Session middleware fixtures ──────────────────────────────────────────────

@pytest.fixture
def mock_session():
    """
    require_session ni o'tkazadi — kesh hit yo'li.

    get_cache to'g'ridan-to'g'ri u_id qaytaradi, shuning uchun DB ga
    so'rov ketmaydi.
    """
    with patch("middleware.require_session.get_cache", return_value=TEST_U_ID):
        yield


@pytest.fixture
def mock_session_miss():
    """require_session ni o'tkazadi — kesh miss, DB dan sessiya topiladi."""
    with patch("middleware.require_session.get_cache", return_value=None), \
         patch("middleware.require_session.fetch_one", return_value={"u_id": TEST_U_ID}), \
         patch("middleware.require_session.set_cache"):
        yield


@pytest.fixture
def mock_no_session():
    """require_session ni rad etadi — na keshda, na DB da sessiya bor."""
    with patch("middleware.require_session.get_cache", return_value=None), \
         patch("middleware.require_session.fetch_one", return_value=None):
        yield
