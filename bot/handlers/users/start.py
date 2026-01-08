from loader import dp
import asyncio
from aiogram import types
from data.database import get_user, new_user
from keyboards.default.main_keyboards import main_manu



@dp.message_handler(commands=["start"])
async def bot_start(message: types.Message):
    user_id = message.from_user.id
    name = message.chat.full_name

    user = get_user(message.chat.id)

    if user:
        await message.answer(f"Sizni botda qayta ko'rib turganimda judaham hursandman, {name}!!",reply_markup=main_manu)
    else:
        if new_user(user_id, name):
            await message.answer(f"Assalomu alekum {name}! Sizni uchbu botda ko'rib turganimdan judahma hursandamn. O'zingiz hoxlagan pastdagi tugmalardan foydalanishingiz mukun.",reply_markup=main_manu)
        else:
            await message.answer("Qandeydur xatolik yuz berdi. Iltimos keyinroq qayta urinib ko'ring!")
