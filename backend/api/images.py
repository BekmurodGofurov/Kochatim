# backend/api/images.py
from flask import Response, request
import requests

from api import api_bp
from config import Config
from middleware.require_api_key import require_api_key
from utils.errors import ok, fail
from db import fetch_one, execute

TELEGRAM_API = "https://api.telegram.org"


@api_bp.post("/img")
@require_api_key
def add_img():
    """
    Bot: POST /api/img {t_id, i_url}
    """
    data = request.get_json(silent=True) or {}
    t_id = data.get("t_id")
    i_url = data.get("i_url")

    if not t_id or not i_url:
        return fail("t_id and i_url required", 400)

    try:
        t_id_int = int(t_id)
    except (ValueError, TypeError):
        return fail("t_id must be an integer", 400)

    # UPSERT logic
    row = fetch_one("SELECT i_id FROM img WHERE t_id=%s", (t_id_int,))
    if row:
        execute("UPDATE img SET i_url=%s, updated_at=CURRENT_TIMESTAMP WHERE t_id=%s", (i_url, t_id_int))
    else:
        execute("INSERT INTO img (t_id, i_url) VALUES (%s, %s)", (t_id_int, i_url))

    return ok({"saved": True})


@api_bp.get("/img/by-type")
@require_api_key
def get_img_by_type():
    """
    Bot: GET /api/img/by-type?t_id=...
    """
    t_id = request.args.get("t_id")
    if not t_id:
        return fail("t_id query param required", 400)

    try:
        t_id_int = int(t_id)
    except (ValueError, TypeError):
        return fail("t_id must be an integer", 400)

    row = fetch_one("SELECT i_url FROM img WHERE t_id=%s", (t_id_int,))
    if not row:
        return ok(None)

    return ok(row.get("i_url"))


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