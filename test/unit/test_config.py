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


# ─── Web client key, trusted proxies, production validation ───────────────────

def reload_without(*names):
    """
    Reload Config with these variables unset *and* backend/.env ignored, so a
    developer's local .env (which may set DB_POOL_MAX=120, say) cannot change
    what the built-in defaults are asserted to be.
    """
    env = {k: v for k, v in os.environ.items() if k not in names}
    with patch.dict(os.environ, env, clear=True), patch("dotenv.load_dotenv"):
        return importlib.reload(config_module).Config


class TestClientKeysAndProxies:
    def test_web_client_key_is_read_and_stripped(self):
        assert reload_config(WEB_CLIENT_KEY="  web-key  ").WEB_CLIENT_KEY == "web-key"

    def test_web_client_key_defaults_to_empty_so_nothing_matches(self):
        assert reload_without("WEB_CLIENT_KEY").WEB_CLIENT_KEY == ""

    def test_pool_default_is_20_per_worker(self):
        """4 gunicorn workers x 100 would overrun Postgres' default 100 connections."""
        assert reload_without("DB_POOL_MAX").DB_POOL_MAX == 20

    def test_trusted_proxies_default_covers_loopback_and_docker(self):
        cfg = reload_without("TRUSTED_PROXIES")
        assert "127.0.0.1" in cfg.TRUSTED_PROXIES and "172.16.0.0/12" in cfg.TRUSTED_PROXIES

    def test_trusted_proxies_are_split_and_stripped(self):
        cfg = reload_config(TRUSTED_PROXIES=" 10.0.0.1 , 192.168.0.0/16,, ")
        assert cfg.TRUSTED_PROXIES == ("10.0.0.1", "192.168.0.0/16")

    def test_empty_trusted_proxies_trusts_nobody(self):
        assert reload_config(TRUSTED_PROXIES="").TRUSTED_PROXIES == ()

    def test_proof_and_initdata_windows_have_safe_defaults(self):
        cfg = reload_without("PROOF_MAX_SKEW_SECONDS", "INITDATA_MAX_AGE_SECONDS")
        assert cfg.PROOF_MAX_SKEW_SECONDS == 60
        assert cfg.INITDATA_MAX_AGE_SECONDS == 3600


class TestValidate:
    GOOD = dict(API_KEY="bot-secret-" + "a" * 30, WEB_CLIENT_KEY="web-public-" + "b" * 30)

    def test_accepts_two_distinct_real_keys(self):
        reload_config(**self.GOOD).validate()

    @pytest.mark.parametrize("env,fragment", [
        ({"API_KEY": ""}, "API_KEY is empty"),
        ({"WEB_CLIENT_KEY": ""}, "WEB_CLIENT_KEY is empty"),
        ({"API_KEY": "same", "WEB_CLIENT_KEY": "same"}, "must differ"),
        ({"API_KEY": "change_me"}, "API_KEY is still the placeholder"),
        ({"WEB_CLIENT_KEY": "change_me"}, "WEB_CLIENT_KEY is still the placeholder"),
    ])
    def test_refuses_unsafe_keys(self, env, fragment):
        cfg = reload_config(**{**self.GOOD, **env})
        with pytest.raises(RuntimeError, match=fragment):
            cfg.validate()

    def test_reports_every_problem_at_once(self):
        cfg = reload_config(API_KEY="", WEB_CLIENT_KEY="")
        with pytest.raises(RuntimeError) as e:
            cfg.validate()
        assert "API_KEY is empty" in str(e.value) and "WEB_CLIENT_KEY is empty" in str(e.value)

    def test_a_production_app_refuses_to_boot_with_bad_keys(self):
        from unittest.mock import patch as _patch
        import app as app_module
        with _patch("app.Config.FLASK_ENV", "production"), \
             _patch("app.Config.WEB_CLIENT_KEY", ""), \
             _patch("extensions.init_pool"), _patch("db_init.init_db"):
            with pytest.raises(RuntimeError, match="WEB_CLIENT_KEY is empty"):
                app_module.create_app()

    def test_a_production_app_boots_with_good_keys(self):
        import app as app_module
        with patch("app.Config.FLASK_ENV", "production"), \
             patch("app.Config.API_KEY", self.GOOD["API_KEY"]), \
             patch("app.Config.WEB_CLIENT_KEY", self.GOOD["WEB_CLIENT_KEY"]), \
             patch("extensions.init_pool"), patch("db_init.init_db"):
            assert app_module.create_app() is not None

    def test_tests_and_dev_are_not_blocked_by_validation(self):
        import app as app_module
        with patch("app.Config.FLASK_ENV", "development"), \
             patch("app.Config.WEB_CLIENT_KEY", ""), \
             patch("extensions.init_pool"), patch("db_init.init_db"):
            assert app_module.create_app() is not None
