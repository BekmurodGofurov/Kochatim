import os
from dotenv import load_dotenv

load_dotenv()

ADMINS = [
    int(x)
    for x in os.getenv("ADMINS", "").split(",")
    if x.strip().isdigit()
]
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
API_URL = os.getenv("API_URL", "").rstrip("/")
WEB_URL = os.getenv("WEB_URL", "https://kochatim.uz").rstrip("/")
API_KEY = os.getenv("API_KEY", "").strip()