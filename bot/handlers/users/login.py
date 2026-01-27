from aiogram.types import Message, ReplyKeyboardRemove
from loader import dp


@dp.message_handler(text="/login")
async def start_sale(message: Message):
    u_id = message.from_user.id
    await message.answer(f"<b>LOGIN WITH USER ID</b>\n\nYour id: <b><code>{u_id}</code></b>")
