from aiogram import types
from loader import dp
from keyboards.default.main_keyboards import get_add_menu

@dp.message_handler(text="Qo'shish")
async def show_add_menu(message: types.Message):
    await message.answer("Nima qo'shmoqchisiz?", reply_markup=get_add_menu())
