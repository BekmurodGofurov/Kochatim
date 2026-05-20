import os
from dotenv import load_dotenv

load_dotenv()

ADMINS = [
    int(x)
    for x in os.getenv("ADMINS", "").split(",")
    if x.strip().isdigit()
]

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN muhit o'zgaruvchisi sozlanmagan! bot/.env faylini tekshiring.")

API_URL = os.getenv("API_URL", "").rstrip("/")
if not API_URL:
    raise RuntimeError("API_URL muhit o'zgaruvchisi sozlanmagan! bot/.env faylini tekshiring.")

API_KEY = os.getenv("API_KEY", "").strip()
if not API_KEY:
    raise RuntimeError("API_KEY muhit o'zgaruvchisi sozlanmagan! bot/.env faylini tekshiring.")

WEB_URL = os.getenv("WEB_URL", "").rstrip("/")
if not WEB_URL:
    raise RuntimeError("WEB_URL muhit o'zgaruvchisi sozlanmagan! bot/.env faylini tekshiring.")