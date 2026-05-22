# backend/utils/telegram_notify.py
import requests
from config import Config


def send_message(chat_id: int, text: str, parse_mode: str = "Markdown") -> None:
    """Telegram botdan foydalanuvchiga xabar yuboradi. Xatolik bo'lsa jimgina o'tkazadi."""
    token = Config.BOT_TOKEN
    if not token or not chat_id:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": parse_mode},
            timeout=5,
        )
    except Exception:
        pass
