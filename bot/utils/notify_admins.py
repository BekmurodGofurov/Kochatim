from aiogram.utils.exceptions import ChatNotFound, BotBlocked
from data.config import ADMINS


async def on_startup_notify(dp):
    if not ADMINS:
        return

    for admin_id in ADMINS:
        try:
            await dp.bot.send_message(admin_id, "Bot ishga tushdi 💡")
        except (ChatNotFound, BotBlocked):
            # Admin botga /start bosmagan yoki bot block qilingan
            continue
        except Exception:
            # boshqa xatolarni ham botni yiqitmaslik uchun yutamiz
            continue