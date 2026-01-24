# backend/api/images.py
from flask import Response
from api import api_bp
from config import Config   # ✅ TO‘G‘RI IMPORT
import requests

TELEGRAM_API = "https://api.telegram.org"


@api_bp.get("/img/<file_id>")
def proxy_telegram_image(file_id: str):
    """
    Telegram file_id -> real image (binary)
    Frontend <img src="/api/img/<file_id>" /> ishlaydi
    """

    BOT_TOKEN = Config.BOT_TOKEN  # ✅ TO‘G‘RI O‘QISH

    if not BOT_TOKEN:
        return Response("BOT_TOKEN not configured", status=500)

    # 1) file_id -> file_path
    tg_get_file_url = f"{TELEGRAM_API}/bot{BOT_TOKEN}/getFile"
    r = requests.get(tg_get_file_url, params={"file_id": file_id}, timeout=10)

    if r.status_code != 200:
        return Response("Telegram getFile failed", status=502)

    data = r.json()
    if not data.get("ok"):
        return Response("Invalid file_id", status=404)

    file_path = data["result"].get("file_path")
    if not file_path:
        return Response("File path not found", status=404)

    # 2) file_path -> real binary
    tg_file_url = f"{TELEGRAM_API}/file/bot{BOT_TOKEN}/{file_path}"
    img_resp = requests.get(tg_file_url, stream=True, timeout=15)

    if img_resp.status_code != 200:
        return Response("Image fetch failed", status=502)

    content_type = img_resp.headers.get("Content-Type", "image/jpeg")

    return Response(
        img_resp.content,
        status=200,
        content_type=content_type,
        headers={
            "Cache-Control": "public, max-age=86400"
        },
    )