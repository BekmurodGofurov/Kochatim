# backend/config.py
import os
from dotenv import load_dotenv

# .env ni har doim yuklash (backend papkadan ishga tushsa ham, snippet bo'lsa ham)
load_dotenv()


class Config:
    DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
    API_KEY = os.getenv("API_KEY", "").strip()
    BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
    TG_BOT_USERNAME = os.getenv("TG_BOT_USERNAME", "").strip().lstrip("@")
    IMGBB_API_KEY = os.getenv("IMGBB_API_KEY", "").strip()

    OTP_TTL_SECONDS = int(os.getenv("OTP_TTL_SECONDS", "120"))
    SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", str(30 * 24 * 3600)))


    DB_POOL_MIN = int(os.getenv("DB_POOL_MIN", "1"))
    DB_POOL_MAX = int(os.getenv("DB_POOL_MAX", "20"))

    FLASK_ENV = os.getenv("FLASK_ENV", "production")