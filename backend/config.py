# backend/config.py
import os
from dotenv import load_dotenv

# __file__ orqali .env ni har doim to'g'ri papkadan topadi
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))


class Config:
    DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
    API_KEY = os.getenv("API_KEY", "").strip()
    BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
    TG_BOT_USERNAME = os.getenv("TG_BOT_USERNAME", "").strip().lstrip("@")
    IMGBB_API_KEY = os.getenv("IMGBB_API_KEY", "").strip()

    OTP_TTL_SECONDS = int(os.getenv("OTP_TTL_SECONDS", "120"))
    SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", str(30 * 24 * 3600)))

    DB_POOL_MIN = int(os.getenv("DB_POOL_MIN", "5"))
    DB_POOL_MAX = int(os.getenv("DB_POOL_MAX", "100"))

    FLASK_ENV = os.getenv("FLASK_ENV", "production")
    PORT = int(os.getenv("PORT", "8000"))

    ALLOWED_ORIGINS: set = set(
        o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()
    )