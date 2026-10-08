"""
Bot test suite — shared fixtures.

Ikki narsa muhim:

1. `bot/data/config.py` import vaqtida `RuntimeError` KO'TARADI, agar
   BOT_TOKEN / API_URL / API_KEY / WEB_URL sozlanmagan bo'lsa. Shuning
   uchun muhit o'zgaruvchilari modul darajasida, har qanday bot
   import'idan oldin o'rnatiladi.

2. `bot/api_client.py` ham API_URL va API_KEY ni import vaqtida o'qiydi
   (`os.getenv` modul darajasida). Keyinchalik `os.environ` ni
   o'zgartirish unga ta'sir qilmaydi — testlar modul global'ini
   to'g'ridan-to'g'ri patch qiladi.

Bot `bot/utils/` papkasiga ega, backend esa `backend/utils/` ga. Ikkisi
bir vaqtda `sys.path` da bo'lsa `import utils...` noto'g'ri paketga
tushadi — shu sababli bot testlari backend'dan ALOHIDA pytest root'ida
(bot/pytest.ini) ishlaydi.
"""
import os
import sys

BOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BOT_DIR not in sys.path:
    sys.path.insert(0, BOT_DIR)

# data/config.py import vaqtida shularni talab qiladi
os.environ.setdefault("BOT_TOKEN", "123456789:TEST_BOT_TOKEN_ABCDEF1234")
os.environ.setdefault("API_URL", "http://backend:8000")
os.environ.setdefault("API_KEY", "test-api-key-12345")
os.environ.setdefault("WEB_URL", "http://localhost:5173")
os.environ.setdefault("ADMINS", "111111,222222")

from unittest.mock import patch

import pytest

TEST_API_URL = "http://backend:8000"
TEST_API_KEY = "test-api-key-12345"
TEST_U_ID = 123456789


@pytest.fixture
def api_client():
    """bot/api_client.py moduli, API_URL/API_KEY test qiymatlari bilan."""
    import api_client as mod

    original = (mod.API_URL, mod.API_KEY, mod._session)
    mod.API_URL = TEST_API_URL
    mod.API_KEY = TEST_API_KEY
    yield mod
    mod.API_URL, mod.API_KEY, mod._session = original


# ─── aiohttp sessiyasini taqlid qilish ───────────────────────────────────────
# `aioresponses` aiohttp 3.14 bilan mos kelmaydi (ClientResponse imzosi
# o'zgargan), aiohttp'ni testda eski versiyaga qadab qo'yish esa test
# muhitini productiondan uzoqlashtiradi. Shuning uchun taqlid aniq
# `session.request(...)` chegarasida qilinadi — bu aiohttp versiyasiga
# bog'liq emas va api_client'ning o'z shartnomasini tekshiradi.

class FakeResponse:
    """`async with session.request(...)` dan qaytadigan obyekt."""

    def __init__(self, status=200, payload=None, json_error=None, text=""):
        self.status = status
        self._payload = payload
        self._json_error = json_error
        self._text = text

    async def json(self, content_type=None):
        if self._json_error is not None:
            raise self._json_error
        return self._payload

    async def text(self):
        return self._text

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return False


class FakeSession:
    """So'rovlarni yozib oladi va navbatga qo'yilgan javoblarni beradi."""

    closed = False

    def __init__(self):
        self.calls = []
        self._queue = []

    def respond(self, status=200, payload=None, json_error=None, text=""):
        self._queue.append(FakeResponse(status, payload, json_error, text))
        return self

    def request(self, method, url, headers=None, json=None, params=None):
        self.calls.append({
            "method": method, "url": url, "headers": headers or {},
            "json": json, "params": params,
        })
        if not self._queue:
            raise AssertionError(f"Kutilmagan so'rov: {method} {url}")
        return self._queue.pop(0)

    @property
    def last(self):
        assert self.calls, "Hech qanday so'rov yuborilmadi"
        return self.calls[-1]


@pytest.fixture
def backend(api_client):
    """api_client ning aiohttp sessiyasini FakeSession bilan almashtiradi."""
    session = FakeSession()
    with patch.object(api_client, "get_session", return_value=session):
        yield session


@pytest.fixture
def database():
    """
    bot/data/database.py moduli — ikkinchi HTTP clienti.

    `api_client` dan mustaqil: o'z API_URL/API_KEY global'lari bor,
    ular ham import vaqtida o'qiladi.
    """
    import data.database as mod

    original = (mod.API_URL, mod.API_KEY, mod._session)
    mod.API_URL = TEST_API_URL
    mod.API_KEY = TEST_API_KEY
    yield mod
    mod.API_URL, mod.API_KEY, mod._session = original


@pytest.fixture
def db_backend(database):
    """data.database ning aiohttp sessiyasini FakeSession bilan almashtiradi."""
    session = FakeSession()
    with patch.object(database, "get_session", return_value=session):
        yield session
