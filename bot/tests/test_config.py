"""
Tests — bot/data/config.py

Bu modul import vaqtida `RuntimeError` ko'taradi, agar majburiy muhit
o'zgaruvchisi yo'q bo'lsa. Bu ataylab: bot tokensiz ishga tushsa,
Telegram'ga ulanmay jimgina "ishlayotgandek" turardi.

Shuning uchun testlar `importlib.reload` ishlatadi — oddiy fixture
import bo'lib bo'lgandan keyin ishlaydi va hech narsani o'zgartirmaydi.
"""
import importlib
import os
from unittest.mock import patch

import pytest

import data.config as config_module

REQUIRED = {
    "BOT_TOKEN": "123456789:TEST_BOT_TOKEN_ABCDEF1234",
    "API_URL": "http://backend:8000",
    "API_KEY": "test-api-key-12345",
    "WEB_URL": "http://localhost:5173",
}


def reload_with(**overrides):
    """config modulini berilgan muhit bilan qayta yuklaydi."""
    env = dict(REQUIRED)
    env.update(overrides)
    with patch.dict(os.environ, env, clear=False):
        return importlib.reload(config_module)


@pytest.fixture(autouse=True)
def restore_module():
    yield
    with patch.dict(os.environ, REQUIRED, clear=False):
        importlib.reload(config_module)


# ─── Majburiy o'zgaruvchilar ─────────────────────────────────────────────────

class TestRequiredVars:
    @pytest.mark.parametrize("var", ["BOT_TOKEN", "API_URL", "API_KEY", "WEB_URL"])
    def test_empty_value_raises_runtime_error(self, var):
        with pytest.raises(RuntimeError):
            reload_with(**{var: ""})

    @pytest.mark.parametrize("var", ["BOT_TOKEN", "API_URL", "API_KEY", "WEB_URL"])
    def test_error_message_names_the_variable(self, var):
        with pytest.raises(RuntimeError, match=var):
            reload_with(**{var: ""})

    @pytest.mark.parametrize("var", ["BOT_TOKEN", "API_URL", "API_KEY", "WEB_URL"])
    def test_whitespace_only_value_raises(self, var):
        # BOT_TOKEN/API_KEY .strip() qiladi; API_URL/WEB_URL .rstrip("/")
        # qiladi, shuning uchun bo'shliq ular uchun o'tib ketadi.
        if var in ("BOT_TOKEN", "API_KEY"):
            with pytest.raises(RuntimeError):
                reload_with(**{var: "   "})
        else:
            mod = reload_with(**{var: "   "})
            assert getattr(mod, var) == "   "

    def test_all_vars_present_loads_cleanly(self):
        mod = reload_with()
        assert mod.BOT_TOKEN == REQUIRED["BOT_TOKEN"]
        assert mod.API_URL == REQUIRED["API_URL"]
        assert mod.API_KEY == REQUIRED["API_KEY"]
        assert mod.WEB_URL == REQUIRED["WEB_URL"]


# ─── Qiymatlarni normallashtirish ────────────────────────────────────────────

class TestNormalisation:
    def test_bot_token_is_stripped(self):
        assert reload_with(BOT_TOKEN="  tok  ").BOT_TOKEN == "tok"

    def test_api_key_is_stripped(self):
        assert reload_with(API_KEY="  key  ").API_KEY == "key"

    def test_api_url_trailing_slash_removed(self):
        """api_client URL ni `API_URL + path` sifatida quradi."""
        assert reload_with(API_URL="http://backend:8000/").API_URL == "http://backend:8000"

    def test_api_url_multiple_trailing_slashes_removed(self):
        assert reload_with(API_URL="http://backend:8000///").API_URL == "http://backend:8000"

    def test_web_url_trailing_slash_removed(self):
        assert reload_with(WEB_URL="http://localhost:5173/").WEB_URL == "http://localhost:5173"


# ─── ADMINS ───────────────────────────────────────────────────────────────────

class TestAdmins:
    def test_parsed_into_list_of_ints(self):
        mod = reload_with(ADMINS="111,222")
        assert mod.ADMINS == [111, 222]

    def test_empty_value_gives_empty_list(self):
        assert reload_with(ADMINS="").ADMINS == []

    def test_non_numeric_entries_are_dropped(self):
        """Yaroqsiz ID ishga tushishni to'xtatmasligi kerak."""
        assert reload_with(ADMINS="111,abc,222").ADMINS == [111, 222]

    def test_whitespace_around_ids_is_tolerated(self):
        assert reload_with(ADMINS=" 111 , 222 ").ADMINS == [111, 222]

    def test_trailing_comma_is_tolerated(self):
        assert reload_with(ADMINS="111,222,").ADMINS == [111, 222]

    def test_single_admin(self):
        assert reload_with(ADMINS="111").ADMINS == [111]

    def test_negative_id_is_dropped(self):
        """isdigit() "-100" uchun False beradi — guruh ID'lari o'tmaydi."""
        assert reload_with(ADMINS="-100,111").ADMINS == [111]

    def test_admins_is_optional(self):
        """
        ADMINS yo'q bo'lsa bot ishga tushadi, shunchaki bildirishnoma
        yubormaydi.

        `load_dotenv` mock qilinadi: modul uni chaqiradi va muhit bo'sh
        bo'lsa haqiqiy `bot/.env` faylidan qiymat o'qib oladi, natijada
        test ishlab turgan mashinaning sozlamasiga bog'liq bo'lib qolardi.

        Patch `dotenv.load_dotenv` ga qo'yiladi, `data.config.load_dotenv`
        ga emas: `importlib.reload` modul tanasini qaytadan bajaradi va
        `from dotenv import load_dotenv` nomni HAQIQIY funksiyaga qayta
        bog'lab, modul atributiga qo'yilgan patch'ni bosib ketadi.
        """
        env = {k: v for k, v in os.environ.items() if k != "ADMINS"}
        env.update(REQUIRED)
        with patch.dict(os.environ, env, clear=True), \
             patch("dotenv.load_dotenv"):
            assert importlib.reload(config_module).ADMINS == []
