from aiogram.types import Message
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text

from loader import dp
from states.state_one import cat_state
from data.database import new_cat, get_all_cat
from keyboards.default.main_keyboards import cat_keyboard, main_manu


@dp.message_handler(Text(equals="Yangi Gruh"), state="*")
async def add_cat_start(message: Message, state: FSMContext):
    await state.finish()
    await message.answer("Yangi guruh nomini yuboring:")
    await cat_state.c_name.set()


@dp.message_handler(state=cat_state.c_name)
async def add_cat_save(message: Message, state: FSMContext):
    u_id = message.from_user.id
    c_name = (message.text or "").strip()

    if not c_name:
        await message.answer("Guruh nomi bo‘sh bo‘lmasin. Qayta yuboring:")
        return

    await new_cat(u_id=int(u_id), c_name=c_name)

    # xohlasa: yangilangan ro'yxatni ko'rsatamiz
    cats = await get_all_cat(u_id)
    if cats:
        await message.answer("✅ Guruh qo‘shildi. Guruhlar:", reply_markup=cat_keyboard(cats))
    else:
        await message.answer("✅ Guruh qo‘shildi.", reply_markup=main_manu)

    await state.finish()