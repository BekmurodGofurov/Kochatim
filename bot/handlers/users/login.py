from aiogram.types import Message
from loader import dp
from api_client import request_login_code, BackendAPIError


@dp.message_handler(text="/login")
async def cmd_login(message: Message):
    user = message.from_user
    try:
        result = await request_login_code(
            u_id=user.id,
            u_name=user.full_name,
            u_username=user.username,
        )
        code = result["code"]
        expires_in = result["expires_in"]
        minutes = expires_in // 60
        await message.answer(
            f"🔐 <b>Kirish kodi:</b>\n\n"
            f"<code>{code}</code>\n\n"
            f"⏱ Bu kod <b>{minutes} daqiqa</b> amal qiladi.\n"
            f"Kodni hech kimga bermang!",
            parse_mode="HTML",
        )
    except BackendAPIError:
        await message.answer("❌ Xatolik yuz berdi. Qayta urinib ko'ring.")
