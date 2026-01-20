from aiogram.types import Message
from aiogram.dispatcher.filters import Text

from loader import dp
from data.database import get_all_cat
from keyboards.default.main_keyboards import cat_keyboard, new_cat


@dp.message_handler(Text(equals="Ko'rish"), state="*")
async def cat_handler(message: Message):
    u_id = message.from_user.id

    cats = await get_all_cat(u_id)  # list[str]
    if not cats:
        await message.answer("Sizda hali guruh yo‘q.", reply_markup=new_cat)
        return

    await message.answer("Guruh tanlang:", reply_markup=cat_keyboard(cats))