"""
Tests — bot/utils/misc/throttling.py va bot/middlewares/throttling.py

`rate_limit` handler funksiyasiga atribut yozadi; `ThrottlingMiddleware`
shu atributlarni o'qib limitni qo'llaydi. Ikkisi juft ishlaydi, shuning
uchun atribut nomlari ikki fayl orasidagi shartnoma — testlar aynan
shu nomlarni tekshiradi.

Butun fayl aiogram'ni talab qiladi — `rate_limit` o'zi toza Python
bo'lsa ham, `bot/utils/__init__.py` ichida `from .notify_admins import ...`
bor, u esa `aiogram.utils.exceptions` ni import qiladi. Ya'ni
`utils.misc.throttling` ni aiogram'siz import qilib bo'lmaydi.

aiogram 2.x Python 3.13 ga o'rnatilmaydi, shuning uchun lokal mashinada
bu fayl o'tkazib yuboriladi. Docker ichida (python:3.11-slim) ishlaydi:
`docker compose -f docker-compose.test.yml run --rm test-bot`.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytest.importorskip(
    "aiogram",
    reason="aiogram o'rnatilmagan (2.x Python 3.13 ni qo'llamaydi) — "
           "bu testlar Docker ichida ishlaydi",
)

from utils.misc.throttling import rate_limit  # noqa: E402


# ─── rate_limit dekoratori ────────────────────────────────────────────────────

class TestRateLimit:
    def test_sets_rate_limit_attribute(self):
        @rate_limit(5)
        def handler():
            pass

        assert handler.throttling_rate_limit == 5

    def test_returns_the_same_function(self):
        def handler():
            pass

        assert rate_limit(5)(handler) is handler

    def test_does_not_set_key_when_omitted(self):
        @rate_limit(5)
        def handler():
            pass

        assert not hasattr(handler, "throttling_key")

    def test_sets_key_when_given(self):
        @rate_limit(5, key="start")
        def handler():
            pass

        assert handler.throttling_key == "start"

    def test_function_still_callable(self):
        @rate_limit(2)
        def handler(x):
            return x * 2

        assert handler(3) == 6

    def test_preserves_function_name(self):
        @rate_limit(2)
        def my_handler():
            pass

        assert my_handler.__name__ == "my_handler"

    def test_works_on_async_functions(self):
        @rate_limit(2, key="async_one")
        async def handler():
            return 1

        assert handler.throttling_rate_limit == 2
        assert handler.throttling_key == "async_one"

    def test_zero_limit_is_stored(self):
        @rate_limit(0)
        def handler():
            pass

        assert handler.throttling_rate_limit == 0

    def test_float_limit_is_stored(self):
        @rate_limit(0.5)
        def handler():
            pass

        assert handler.throttling_rate_limit == 0.5


# ─── ThrottlingMiddleware ─────────────────────────────────────────────────────

from aiogram.utils.exceptions import Throttled  # noqa: E402

from middlewares.throttling import ThrottlingMiddleware  # noqa: E402

pytestmark = pytest.mark.asyncio


@pytest.fixture
def dispatcher():
    """Dispatcher.get_current() ni mock qiladi."""
    dp = MagicMock()
    dp.throttle = AsyncMock()
    with patch("middlewares.throttling.Dispatcher.get_current", return_value=dp):
        yield dp


def set_current_handler(handler):
    """current_handler ContextVar ini o'rnatadi."""
    return patch("middlewares.throttling.current_handler.get", return_value=handler)


class TestThrottlingMiddlewareInit:
    def test_stores_default_limit(self):
        from aiogram.dispatcher import DEFAULT_RATE_LIMIT

        mw = ThrottlingMiddleware()
        assert mw.rate_limit == DEFAULT_RATE_LIMIT

    def test_stores_custom_limit(self):
        assert ThrottlingMiddleware(limit=3).rate_limit == 3

    def test_default_key_prefix(self):
        assert ThrottlingMiddleware().prefix == "antiflood_"

    def test_custom_key_prefix(self):
        assert ThrottlingMiddleware(key_prefix="kochatim_").prefix == "kochatim_"


class TestOnProcessMessage:
    async def test_uses_handler_rate_limit_when_set(self, dispatcher):
        @rate_limit(7)
        def my_handler():
            pass

        mw = ThrottlingMiddleware(limit=1)
        with set_current_handler(my_handler):
            await mw.on_process_message(MagicMock(), {})
        assert dispatcher.throttle.call_args.kwargs["rate"] == 7

    async def test_falls_back_to_middleware_limit(self, dispatcher):
        def plain_handler():
            pass

        mw = ThrottlingMiddleware(limit=4)
        with set_current_handler(plain_handler):
            await mw.on_process_message(MagicMock(), {})
        assert dispatcher.throttle.call_args.kwargs["rate"] == 4

    async def test_uses_handler_key_when_set(self, dispatcher):
        @rate_limit(2, key="start_cmd")
        def my_handler():
            pass

        mw = ThrottlingMiddleware()
        with set_current_handler(my_handler):
            await mw.on_process_message(MagicMock(), {})
        assert dispatcher.throttle.call_args[0][0] == "start_cmd"

    async def test_derives_key_from_handler_name(self, dispatcher):
        def my_handler():
            pass

        mw = ThrottlingMiddleware(key_prefix="pfx")
        with set_current_handler(my_handler):
            await mw.on_process_message(MagicMock(), {})
        assert dispatcher.throttle.call_args[0][0] == "pfx_my_handler"

    async def test_uses_generic_key_without_a_handler(self, dispatcher):
        mw = ThrottlingMiddleware(key_prefix="pfx")
        with set_current_handler(None):
            await mw.on_process_message(MagicMock(), {})
        assert dispatcher.throttle.call_args[0][0] == "pfx_message"

    async def test_passes_through_when_not_throttled(self, dispatcher):
        def my_handler():
            pass

        mw = ThrottlingMiddleware()
        with set_current_handler(my_handler):
            await mw.on_process_message(MagicMock(), {})  # xato ko'tarilmasligi kerak

    async def test_cancels_handler_when_throttled(self, dispatcher):
        from aiogram.dispatcher.handler import CancelHandler

        def my_handler():
            pass

        dispatcher.throttle.side_effect = Throttled(key="k", rate=1, exceeded_count=1)
        mw = ThrottlingMiddleware()
        message = MagicMock()
        message.reply = AsyncMock()

        with set_current_handler(my_handler), pytest.raises(CancelHandler):
            await mw.on_process_message(message, {})

    async def test_warns_the_user_on_first_throttle(self, dispatcher):
        from aiogram.dispatcher.handler import CancelHandler

        def my_handler():
            pass

        dispatcher.throttle.side_effect = Throttled(key="k", rate=1, exceeded_count=1)
        mw = ThrottlingMiddleware()
        message = MagicMock()
        message.reply = AsyncMock()

        with set_current_handler(my_handler), pytest.raises(CancelHandler):
            await mw.on_process_message(message, {})
        message.reply.assert_awaited_once()


class TestMessageThrottled:
    async def test_replies_on_first_exceed(self):
        mw = ThrottlingMiddleware()
        message = MagicMock()
        message.reply = AsyncMock()
        await mw.message_throttled(message, Throttled(key="k", rate=1, exceeded_count=1))
        message.reply.assert_awaited_once()

    async def test_replies_on_second_exceed(self):
        mw = ThrottlingMiddleware()
        message = MagicMock()
        message.reply = AsyncMock()
        await mw.message_throttled(message, Throttled(key="k", rate=1, exceeded_count=2))
        message.reply.assert_awaited_once()

    async def test_stays_silent_after_two_exceeds(self):
        """
        Flood davom etsa bot jim bo'ladi — aks holda o'zi ham flood
        qilib, Telegram rate limitiga tushardi.
        """
        mw = ThrottlingMiddleware()
        message = MagicMock()
        message.reply = AsyncMock()
        await mw.message_throttled(message, Throttled(key="k", rate=1, exceeded_count=3))
        message.reply.assert_not_awaited()

    async def test_reply_text_is_in_uzbek(self):
        mw = ThrottlingMiddleware()
        message = MagicMock()
        message.reply = AsyncMock()
        await mw.message_throttled(message, Throttled(key="k", rate=1, exceeded_count=1))
        assert "so'rov" in message.reply.call_args[0][0]
