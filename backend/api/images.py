# backend/api/images.py
from flask import Response, current_app, request
import requests

from api import api_bp
from config import Config
from middleware.require_api_key import require_api_key
from utils.errors import ok, fail
from db import fetch_one, execute
from middleware.require_session import require_session
from utils.cache import get_cache, set_cache
from utils.device import get_client_ip
from utils import ratelimit
from utils.images_v2 import process_image_input

TELEGRAM_API = "https://api.telegram.org"

# The proxy turns one cheap request into two slow ones against Telegram, so
# it is the easiest route to tie workers up with. Bound it three ways: only
# ids we handed out are fetched, each IP gets a request budget, and the size
# and type of what comes back is capped.
_IMG_RATE_LIMIT = 120          # requests per IP per window
_IMG_RATE_WINDOW = 60          # seconds
_IMG_KNOWN_TTL = 3600          # how long "this id is ours" is remembered
_MAX_IMAGE_BYTES = 10 * 1024 * 1024


@api_bp.post("/img")
@require_api_key
def add_img():
    """
    Bot: POST /api/img {t_id, i_url}
    """
    data = request.get_json(silent=True) or {}
    t_id = data.get("t_id")
    i_url_raw = data.get("i_url")

    if not t_id or not i_url_raw:
        return fail("t_id and i_url required", 400)

    # Smart convert (Telegram ID -> ImgBB URL)
    i_url = process_image_input(i_url_raw)

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


@api_bp.post("/img/upload")
@require_session
def upload_img_direct():
    """
    Website: POST /api/img/upload (form-data)
    """
    if 'image' not in request.files:
        return fail("No image file", 400)
    
    file = request.files['image']
    if file.filename == '':
        return fail("No selected file", 400)

    from utils.images_v2 import upload_to_imgbb
    
    img_content = file.read()
    url = upload_to_imgbb(img_content)
    
    if not url:
        return fail("Upload to ImgBB failed", 500)
        
    return ok({"url": url})


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


def _is_known_file_id(file_id: str) -> bool:
    """True only for a file_id stored as a user photo or a variety image."""
    key = f"img_known_{file_id}"
    if get_cache(key):
        return True
    row = fetch_one(
        """
        SELECT 1 AS known FROM users WHERE u_photo = %s
        UNION ALL
        SELECT 1 FROM img WHERE i_url = %s
        LIMIT 1
        """,
        (file_id, file_id),
    )
    if row:
        set_cache(key, True, ttl=_IMG_KNOWN_TTL)
        return True
    return False


def _telegram_failed(stage: str, exc: Exception):
    # Log the exception *type* only: a requests error message contains the
    # full URL, and the URL contains the bot token.
    current_app.logger.warning("telegram image %s failed: %s", stage, type(exc).__name__)
    return Response("Image unavailable", status=502)


@api_bp.get("/img/<file_id>")
def proxy_telegram_image(file_id: str):
    """
    Telegram file_id -> real image (binary)
    Frontend <img src="/api/img/<file_id>?k=<client key>" /> ishlaydi
    """

    bot_token = Config.BOT_TOKEN

    if not bot_token:
        return Response("Image service not configured", status=500)

    ip = get_client_ip(request) or "unknown"
    used = ratelimit.record("img", ip, _IMG_RATE_WINDOW)
    if used is not None and used > _IMG_RATE_LIMIT:
        resp = Response("Too many requests", status=429)
        resp.headers["Retry-After"] = str(ratelimit.retry_after(_IMG_RATE_WINDOW))
        return resp

    # Never spend a Telegram round-trip on an id nobody stored.
    if not _is_known_file_id(file_id):
        return Response("Not found", status=404)

    # 1) file_id -> file_path
    try:
        r = requests.get(f"{TELEGRAM_API}/bot{bot_token}/getFile",
                         params={"file_id": file_id}, timeout=10)
    except requests.RequestException as e:
        return _telegram_failed("getFile", e)

    if r.status_code != 200:
        return Response("Telegram getFile failed", status=502)

    data = r.json()
    if not data.get("ok"):
        return Response("Invalid file_id", status=404)

    file_path = data["result"].get("file_path")
    if not file_path:
        return Response("File path not found", status=404)

    # 2) file_path -> real binary
    try:
        img_resp = requests.get(f"{TELEGRAM_API}/file/bot{bot_token}/{file_path}",
                                stream=True, timeout=15)
    except requests.RequestException as e:
        return _telegram_failed("download", e)

    if img_resp.status_code != 200:
        return Response("Image fetch failed", status=502)

    content_type = img_resp.headers.get("Content-Type", "image/jpeg")
    kind = content_type.split(";")[0].strip().lower()
    # This is served from the API's own origin, so only real images pass:
    # not HTML, and not SVG (which can carry script). octet-stream is allowed
    # because Telegram's file server uses it for some photos and an <img>
    # decodes the bytes whatever the header says.
    if kind == "image/svg+xml" or not (kind.startswith("image/") or kind == "application/octet-stream"):
        return Response("Not an image", status=502)

    declared = img_resp.headers.get("Content-Length", "")
    if declared.isdigit() and int(declared) > _MAX_IMAGE_BYTES:
        return Response("Image too large", status=502)

    body = img_resp.content
    if len(body) > _MAX_IMAGE_BYTES:
        return Response("Image too large", status=502)

    return Response(
        body,
        status=200,
        content_type=content_type,
        headers={
            "Cache-Control": "public, max-age=86400",
            "X-Content-Type-Options": "nosniff",
            # Belt and braces if someone opens the URL directly.
            "Content-Security-Policy": "default-src 'none'; sandbox",
        },
    )
