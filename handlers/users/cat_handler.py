from aiogram.types import Message, ReplyKeyboardRemove
from loader import dp
from data.database import get_all_cat
from keyboards.default.main_keyboards import cat_keyboard

@dp.message_handler(commands="clear_k")
async def k_remove(message: Message):

    await message.answer("Rreplay keyboards are removed", reply_markup=ReplyKeyboardRemove())


@dp.message_handler(lambda message: message.text == "Ko'rish")
async def cat_handler(message: Message):
    cat = get_all_cat(message.from_user.id)
    n = len(cat)
    keyboard = cat_keyboard(cat)
    await message.answer(f"Sizdagi Gurhlar soni <b>{n}ta</b>", reply_markup=keyboard)
