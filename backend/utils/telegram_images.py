# backend/utils/telegram_images.py
import os
import json
import urllib.request
import urllib.parse

# Oddiy cache: bir server run ichida qayta-qayta getFile urmaslik uchun
_FILE_PATH_CACHE = {}

def _bot_token():
    # Sizda token qayerda saqlangan bo‘lsa shu yerga moslab o‘zgartiring:
    # .env -> TELEGRAM_BOT_TOKEN
    return os.getenv("BOT_TOKEN", "")

def file_id_to_web_url(file_id: str) -> str | None:
    """
    Telegram file_id -> public downloadable URL
    https://api.telegram.org/file/bot<TOKEN>/<file_path>
    """
    if not file_id:
        return None

    token = _bot_token()
    if not token:
        return None

    if file_id in _FILE_PATH_CACHE:
        file_path = _FILE_PATH_CACHE[file_id]
        return f"https://api.telegram.org/file/bot{token}/{file_path}" if file_path else None

    try:
        q = urllib.parse.urlencode({"file_id": file_id})
        url = f"https://api.telegram.org/bot{token}/getFile?{q}"

        with urllib.request.urlopen(url, timeout=8) as resp:
            raw = resp.read().decode("utf-8")
            data = json.loads(raw)

        if not data.get("ok"):
            _FILE_PATH_CACHE[file_id] = None
            return None

        file_path = data["result"].get("file_path")
        _FILE_PATH_CACHE[file_id] = file_path

        return f"https://api.telegram.org/file/bot{token}/{file_path}" if file_path else None
    except Exception:
        _FILE_PATH_CACHE[file_id] = None
        return None