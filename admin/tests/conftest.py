"""
Admin panel test suite — shared fixtures.

`admin/app.py` import vaqtida uchta ishni bajaradi, uchalasi ham testda
to'xtatilishi kerak:

1. `SocketIO(app, async_mode='gevent')` — gevent o'rnatilmagan muhitda
   yiqiladi. Mock qilinadi; WebSocket emit'lari `socketio.emit` chaqiruvi
   darajasida tekshiriladi.
2. `redis.Redis(...)` — haqiqiy clientni yaratadi. fakeredis bilan
   almashtiriladi, shuning uchun hisoblagich kodi haqiqatda ishlaydi.
3. `redis_listener` thread'ini ishga tushiradi — abadiy `pubsub.listen()`
   tsikli. Thread.start() to'xtatiladi; listener alohida chaqirib sinaladi.
"""
import os
import sys
import threading
from unittest.mock import MagicMock, patch

ADMIN_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ADMIN_DIR not in sys.path:
    sys.path.insert(0, ADMIN_DIR)

os.environ.setdefault("REDIS_HOST", "127.0.0.1")
os.environ.setdefault("REDIS_PORT", "6379")
os.environ.setdefault("REDIS_PASSWORD", "")
os.environ.setdefault("PORT", "9000")

import fakeredis
import pytest

fake_redis = fakeredis.FakeRedis(decode_responses=True)


def _import_admin_app():
    """admin.app ni tashqi bog'liqliklarsiz import qiladi."""
    with patch("redis.Redis", return_value=fake_redis), \
         patch("flask_socketio.SocketIO", return_value=MagicMock()), \
         patch.object(threading.Thread, "start", lambda self: None):
        import app as admin_app

        return admin_app


admin_app = _import_admin_app()

# Import paytida yaratilgan client fakeredis bo'lmasa, globalni almashtiramiz
# (patch("redis.Redis") import tartibiga qarab o'tmay qolishi mumkin).
admin_app.redis_client = fake_redis


@pytest.fixture
def module():
    """admin/app.py moduli."""
    return admin_app


@pytest.fixture
def app():
    admin_app.app.config["TESTING"] = True
    return admin_app.app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def redis_conn():
    return fake_redis


@pytest.fixture
def socketio():
    """Mock qilingan SocketIO — emit chaqiruvlarini tekshirish uchun."""
    mock = MagicMock()
    with patch.object(admin_app, "socketio", mock):
        yield mock


@pytest.fixture(autouse=True)
def clear_redis():
    fake_redis.flushall()
    yield
    fake_redis.flushall()
