from aiogram.types import Message
from loader import dp
from api_client import get_partners, BackendAPIError


@dp.message_handler(commands=["hamkorlar"])
async def cmd_hamkorlar(message: Message):
    u_id = message.from_user.id
    try:
        partners = await get_partners(u_id)
    except BackendAPIError:
        await message.answer("❌ Xatolik yuz berdi. Qayta urinib ko'ring.")
        return

    if not partners:
        await message.answer("Hozircha hamkorlar yo'q.\n\nHamkor qo'shish uchun veb-saytga kiring.")
        return

    lines = ["👥 *Hamkorlaringiz:*\n"]
    for p in partners:
        name = p.get("u_name") or str(p.get("u_id"))
        username = p.get("u_username")
        line = f"• {name}"
        if username:
            line += f" (@{username})"
        lines.append(line)

    await message.answer("\n".join(lines), parse_mode="Markdown")
