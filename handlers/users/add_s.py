# data.database ga endi new_seedling funksiyasi ham qo'shilishi kerak

from aiogram.types import Message, ReplyKeyboardRemove
from loader import dp
from aiogram.dispatcher import FSMContext
from states.state_one import sel_state
from data.database import get_all_cat, get_cat_id, get_all_ty
from keyboards.default.main_keyboards import cat_keyboard, ty_keyboard, main_manu
from data.database import new_seedling  , get_type_id


# Foydalanuvchi biron tugmani bosganda ishga tushadi (masalan, "Ko'chat qo'shish")
@dp.message_handler(text="Ko'chat Qo'shish")
async def start_sel(message: Message):
    cats = get_all_cat(message.from_user.id)
    keyboard = cat_keyboard(cats)
    await message.answer("Ko'chat sonini kiritmoqchi bo'lgan **Gruh**ni tanlang:", reply_markup=keyboard)
    await sel_state.c_id.set()


# Gruhni tekshirish va Navni chiqarish (Types)
@dp.message_handler(state=sel_state.c_id)
async def select_category(message: Message, state: FSMContext):
    u_id = message.from_user.id
    c_name = message.text

    c_id = get_cat_id(u_id, c_name)

    if c_id:
        await state.update_data(c_id=c_id)
        types = get_all_ty(c_id, u_id)
        keyboard = ty_keyboard(types)

        await message.answer(f"Tanlangan Gruh: **{c_name}**. Endi **Nav**ni tanlang:", reply_markup=keyboard)
        await sel_state.t_id.set()  # Keyingi state ga o'tamiz
    else:
        await message.answer("Iltimos, mavjud Gruh nomini tanlang.")


# Navni tanlash va 1-sifat sonini so'rash
@dp.message_handler(state=sel_state.t_id)
async def select_type(message: Message, state: FSMContext):
    u_id = message.from_user.id
    t_name = message.text
    data = await state.get_data()
    c_id = data['c_id']
    t_id = get_type_id(c_id, u_id, t_name)

    if t_id:
        await state.update_data(t_id=t_id)
        await message.answer("Iltimos, **1-sifat ko'chatlar sonini** kiriting (raqamda):",
                             reply_markup=ReplyKeyboardRemove())
        await sel_state.cuol_1.set()
    else:
        await message.answer("Iltimos, mavjud Nav nomini tanlang.")


@dp.message_handler(state=sel_state.cuol_1)
async def add_q1(message: Message, state: FSMContext):
    try:
        q1 = int(message.text)
        await state.update_data(cuol_1=q1)
        await message.answer("Endi **2-sifat ko'chatlar sonini** kiriting (raqamda yoki 0):")
        await sel_state.cuol_2.set()
    except ValueError:
        await message.answer("Iltimos, son kiriting.")


# 2-sifat sonini kiritish
@dp.message_handler(state=sel_state.cuol_2)
async def add_q2(message: Message, state: FSMContext):
    try:
        q2 = int(message.text)
        await state.update_data(cuol_2=q2)
        await message.answer("Nihoyat, **3-sifat ko'chatlar sonini** kiriting (raqamda yoki 0):")
        await sel_state.cuol_3.set()
    except ValueError:
        await message.answer("Iltimos, son kiriting.")


# 3-sifat sonini kiritish va DBga saqlash
@dp.message_handler(state=sel_state.cuol_3)
async def add_q3(message: Message, state: FSMContext):
    try:
        q3 = int(message.text)
        data = await state.get_data()
        u_id = message.from_user.id

        # new_seedling funksiyasiga faqat kerakli ma'lumotlarni beramiz
        new_seedling(
            u_id=u_id,
            t_id=data['t_id'],
            q1=data['cuol_1'],
            q2=data['cuol_2'],
            q3=q3
        )

        await message.answer("Ko'chatlar soni yangilandi!", reply_markup=main_manu)
        await state.finish()
    except ValueError:
        await message.answer("Iltimos, faqat son kiriting.")