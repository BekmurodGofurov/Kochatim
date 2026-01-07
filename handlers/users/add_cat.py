from aiogram.types import Message, ReplyKeyboardRemove
from loader import dp
from aiogram.dispatcher import FSMContext
from states.state_one import cat_state
from data.database import new_cat
from keyboards.default.main_keyboards import new_type,main_manu
import datetime

@dp.message_handler(lambda message: message.text == "Yangi Gruh")
async def add_c(message: Message):
  await message.answer(f"Gruhga nom bering!", reply_markup=ReplyKeyboardRemove())
  await cat_state.c_name.set()

@dp.message_handler(state=cat_state.c_name)
async def add_by(message: Message, state: FSMContext):
    text = message.text
    await state.update_data(c_name=text)
    data = await state.get_data()
    c_name = data.get("c_name")
    u_id = message.from_user.id
    if new_cat(u_id, c_name):
        await message.answer(f"Siz yuborgan Gruh malumotlar omboriga qo'shildi!!", reply_markup = new_type)
    else:
        await message.answer(f"Siz yuborgan Gruh nomi allaqachon mavjud!\n\nIltimos bohsqa bir nom bering", reply_markup=main_manu)
        await cat_state.c_name.set()
    await state.reset_state(with_data=True)