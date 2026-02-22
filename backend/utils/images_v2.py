# backend/utils/images_v2.py
import requests
import base64
from config import Config

def upload_to_imgbb(image_content: bytes) -> str | None:
    """
    Binary rasm-ni ImgBB-ga yuklaydi va URL-ni qaytaradi.
    """
    if not Config.IMGBB_API_KEY:
        print("[ERROR] IMGBB_API_KEY not configured")
        return None

    try:
        url = "https://api.imgbb.com/1/upload"
        payload = {
            "key": Config.IMGBB_API_KEY,
            "image": base64.b64encode(image_content).decode("utf-8"),
        }
        res = requests.post(url, data=payload, timeout=30)
        res_data = res.json()

        if res_data.get("success"):
            return res_data["data"]["url"]
        else:
            print(f"[IMGBB ERROR] {res_data}")
            return None
    except Exception as e:
        print(f"[IMGBB EXCEPTION] {e}")
        return None

def telegram_to_imgbb(file_id: str) -> str | None:
    """
    Telegram file_id ni ImgBB URL-ga aylantiradi.
    """
    if not Config.BOT_TOKEN:
        print("[ERROR] BOT_TOKEN not configured")
        return None

    try:
        # 1. getFile
        get_file_url = f"https://api.telegram.org/bot{Config.BOT_TOKEN}/getFile"
        r = requests.get(get_file_url, params={"file_id": file_id}, timeout=10)
        data = r.json()

        if not data.get("ok"):
            print(f"[TG ERROR] getFile failed for {file_id}")
            return None

        file_path = data["result"].get("file_path")
        if not file_path:
            return None

        # 2. Download binary
        file_url = f"https://api.telegram.org/file/bot{Config.BOT_TOKEN}/{file_path}"
        img_res = requests.get(file_url, timeout=20)
        if img_res.status_code != 200:
            return None

        # 3. Upload to ImgBB
        return upload_to_imgbb(img_res.content)
    except Exception as e:
        print(f"[TG TO IMGBB EXCEPTION] {e}")
        return None

def process_image_input(input_val: str) -> str:
    """
    Agar input_val URL bo'lsa (http/https) -> qaytaradi.
    Agar Telegram ID bo'lsa (AgACAg...) -> ImgBB-ga yuklab URL-ni qaytaradi.
    Xatolik bo'lsa originalni qaytaradi (fallback).
    """
    if not input_val:
        return input_val

    # Agar allaqachon URL bo'lsa
    if input_val.startswith("http://") or input_val.startswith("https://"):
        return input_val

    # Telegram file_id bo'lishi mumkin (odatda uzun va URL-ga o'xshamaydi)
    # Biz urinib ko'ramiz
    smart_url = telegram_to_imgbb(input_val)
    if smart_url:
        return smart_url

    return input_val
