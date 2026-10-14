# backend/config.py
import os
from dotenv import load_dotenv

# __file__ orqali .env ni har doim to'g'ri papkadan topadi
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))


class Config:
    DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
    # Bot <-> backend shared secret (X-API-KEY). Never shipped to a browser.
    API_KEY = os.getenv("API_KEY", "").strip()
    # Identifies the web client (X-Client-Key). It is baked into the
    # browser bundle, so it is NOT a secret: it only keeps scanners and
    # curl out. The user's real credential is the session token plus the
    # device key it is bound to (middleware/require_session.py).
    WEB_CLIENT_KEY = os.getenv("WEB_CLIENT_KEY", "").strip()
    # Signs partner-invite links. Separate from API_KEY so the bot key can be
    # rotated without invalidating every invite already sent; when unset it
    # falls back to API_KEY, which is what existing deployments already use.
    INVITE_SECRET = os.getenv("INVITE_SECRET", "").strip()
    BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
    TG_BOT_USERNAME = os.getenv("TG_BOT_USERNAME", "").strip().lstrip("@")
    IMGBB_API_KEY = os.getenv("IMGBB_API_KEY", "").strip()
    ADMINS = os.getenv("ADMINS", "").strip()

    OTP_TTL_SECONDS = int(os.getenv("OTP_TTL_SECONDS", "120"))
    SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", str(30 * 24 * 3600)))

    # Device-bound sessions: a request proof older than this is refused,
    # and its nonce is remembered for as long again so it cannot be replayed.
    PROOF_MAX_SKEW_SECONDS = int(os.getenv("PROOF_MAX_SKEW_SECONDS", "60"))

    # Telegram Mini App initData older than this is refused (replay window).
    INITDATA_MAX_AGE_SECONDS = int(os.getenv("INITDATA_MAX_AGE_SECONDS", "3600"))

    DB_POOL_MIN = int(os.getenv("DB_POOL_MIN", "5"))
    # Per gunicorn worker (4 of them) against Postgres' default limit of 100.
    DB_POOL_MAX = int(os.getenv("DB_POOL_MAX", "20"))

    FLASK_ENV = os.getenv("FLASK_ENV", "production")
    PORT = int(os.getenv("PORT", "8000"))

    ALLOWED_ORIGINS: set = set(
        o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()
    )

    # Peers whose X-Real-IP header we believe. Only our own nginx (loopback,
    # or the Docker bridge gateway it arrives through) may set it; for any
    # other peer the TCP address is the client address.
    TRUSTED_PROXIES: tuple = tuple(
        p.strip()
        for p in os.getenv("TRUSTED_PROXIES", "127.0.0.1,::1,172.16.0.0/12").split(",")
        if p.strip()
    )

    @classmethod
    def validate(cls):
        """Refuse to boot a production backend whose keys cannot be trusted."""
        problems = []
        if not cls.API_KEY:
            problems.append("API_KEY is empty")
        if not cls.WEB_CLIENT_KEY:
            problems.append("WEB_CLIENT_KEY is empty")
        if cls.API_KEY and cls.API_KEY == cls.WEB_CLIENT_KEY:
            problems.append("WEB_CLIENT_KEY must differ from API_KEY "
                            "(the web key is public; the bot key is not)")
        for name in ("API_KEY", "WEB_CLIENT_KEY"):
            if getattr(cls, name) == "change_me":
                problems.append(f"{name} is still the placeholder")
        if problems:
            raise RuntimeError("Invalid configuration: " + "; ".join(problems))
