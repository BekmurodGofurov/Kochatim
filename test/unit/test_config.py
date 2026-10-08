"""
Unit tests — backend/config.py

Config klass TANASI import vaqtida bir marta bajariladi, shuning uchun
`os.environ` ni keyinroq o'zgartirish Config ga ta'sir qilmaydi. Testlar
shu sababli modulni `importlib.reload` orqali qayta yuklaydi.

Bu xatti-harakatni bilish muhim: conftest muhit o'zgaruvchilarini
har qanday backend import'idan OLDIN o'rnatishi shu sababdan.
"""
import importlib
import os
from unittest.mock import patch

import pytest

import config as config_module


def reload_config(**env):
    """Berilgan muhit bilan config modulini qayta yuklaydi."""
    with patch.dict(os.environ, env, clear=False):
        # load_dotenv backend/.env ni o'qiydi va mavjud qiymatlarni
        # ustiga yozmaydi, shuning uchun patch.dict yetarli.
        return importlib.reload(config_module).Config


@pytest.fixture(autouse=True)
def restore_config():
    yield
    importlib.reload(config_module)


# ─── Qiymatlarni o'qish ───────────────────────────────────────────────────────

class TestConfigValues:
    def test_reads_values_seeded_by_conftest(self):
        assert config_module.Config.API_KEY == "test-api-key-12345"
        assert config_module.Config.DATABASE_URL.startswith("postgresql://")

    def test_strips_surrounding_whitespace(self):
        cfg = reload_config(API_KEY="  spaced-key  ")
        assert cfg.API_KEY == "spaced-key"

    def test_bot_username_strips_leading_at(self):
        """Telegram deep-link quruvchi kod "@" ni ikki marta qo'ymasligi uchun."""
        cfg = reload_config(TG_BOT_USERNAME="@kochatim_bot")
        assert cfg.TG_BOT_USERNAME == "kochatim_bot"

    def test_bot_username_without_at_unchanged(self):
        cfg = reload_config(TG_BOT_USERNAME="kochatim_bot")
        assert cfg.TG_BOT_USERNAME == "kochatim_bot"


# ─── Sonli qiymatlar ──────────────────────────────────────────────────────────

class TestNumericConfig:
    def test_int_fields_are_ints(self):
        cfg = config_module.Config
        for field in ("OTP_TTL_SECONDS", "SESSION_TTL_SECONDS",
                      "DB_POOL_MIN", "DB_POOL_MAX", "PORT"):
            assert isinstance(getattr(cfg, field), int), field

    def test_otp_ttl_from_env(self):
        assert reload_config(OTP_TTL_SECONDS="300").OTP_TTL_SECONDS == 300

    def test_session_ttl_from_env(self):
        assert reload_config(SESSION_TTL_SECONDS="3600").SESSION_TTL_SECONDS == 3600

    def test_pool_bounds_from_env(self):
        cfg = reload_config(DB_POOL_MIN="2", DB_POOL_MAX="20")
        assert (cfg.DB_POOL_MIN, cfg.DB_POOL_MAX) == (2, 20)

    def test_non_numeric_int_field_raises_at_import(self):
        """
        Yaroqsiz qiymat ishga tushishda darhol yiqiladi — bu yashirin
        noto'g'ri sozlamadan yaxshiroq.
        """
        with pytest.raises(ValueError):
            reload_config(PORT="not-a-number")


# ─── ALLOWED_ORIGINS ──────────────────────────────────────────────────────────

class TestAllowedOrigins:
    def test_parsed_into_a_set(self):
        assert isinstance(config_module.Config.ALLOWED_ORIGINS, set)

    def test_splits_on_comma(self):
        cfg = reload_config(ALLOWED_ORIGINS="http://a.com,http://b.com")
        assert cfg.ALLOWED_ORIGINS == {"http://a.com", "http://b.com"}

    def test_strips_whitespace_around_each_origin(self):
        cfg = reload_config(ALLOWED_ORIGINS=" http://a.com , http://b.com ")
        assert cfg.ALLOWED_ORIGINS == {"http://a.com", "http://b.com"}

    def test_drops_empty_entries(self):
        cfg = reload_config(ALLOWED_ORIGINS="http://a.com,,  ,http://b.com")
        assert cfg.ALLOWED_ORIGINS == {"http://a.com", "http://b.com"}

    def test_empty_value_gives_empty_set(self):
        """
        Bo'sh ALLOWED_ORIGINS — hamma origin rad etiladi (CORS "null"),
        hammasi ruxsat etilishi EMAS.
        """
        assert reload_config(ALLOWED_ORIGINS="").ALLOWED_ORIGINS == set()

    def test_single_origin(self):
        cfg = reload_config(ALLOWED_ORIGINS="http://localhost:5173")
        assert cfg.ALLOWED_ORIGINS == {"http://localhost:5173"}


# ─── Standart qiymatlar ───────────────────────────────────────────────────────

class TestDefaults:
    def test_missing_secrets_default_to_empty_string(self):
        """
        Sir yo'q bo'lsa Config bo'sh satr beradi (import vaqtida
        yiqilmaydi). Himoya o'rni — require_api_key, u bo'sh kalitni
        SERVER_MISCONFIG bilan rad etadi.
        """
        with patch.dict(os.environ, {"API_KEY": "", "BOT_TOKEN": ""}, clear=False):
            cfg = importlib.reload(config_module).Config
            assert cfg.API_KEY == ""
            assert cfg.BOT_TOKEN == ""

    def test_default_otp_ttl_is_120(self):
        env = {k: v for k, v in os.environ.items() if k != "OTP_TTL_SECONDS"}
        with patch.dict(os.environ, env, clear=True):
            assert importlib.reload(config_module).Config.OTP_TTL_SECONDS == 120

    def test_default_session_ttl_is_30_days(self):
        env = {k: v for k, v in os.environ.items() if k != "SESSION_TTL_SECONDS"}
        with patch.dict(os.environ, env, clear=True):
            cfg = importlib.reload(config_module).Config
            assert cfg.SESSION_TTL_SECONDS == 30 * 24 * 3600

    def test_default_port_is_8000(self):
        env = {k: v for k, v in os.environ.items() if k != "PORT"}
        with patch.dict(os.environ, env, clear=True):
            assert importlib.reload(config_module).Config.PORT == 8000

    def test_default_flask_env_is_production(self):
        """Standart holat xavfsiz bo'lishi kerak — debug o'chiq."""
        env = {k: v for k, v in os.environ.items() if k != "FLASK_ENV"}
        with patch.dict(os.environ, env, clear=True):
            assert importlib.reload(config_module).Config.FLASK_ENV == "production"
