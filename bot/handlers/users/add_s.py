from aiogram.types import Message, ReplyKeyboardRemove
from loader import dp
from aiogram.dispatcher import FSMContext
from states.state_one import sel_state

from data.database import (
    get_all_cat,
    get_cat_id,
    get_all_ty,
    new_seedling,
    get_type_id,
)
from keyboards.default.main_keyboards import cat_keyboard, ty_keyboard, main_manu


@dp.message_handler(text="Ko'chat qo'shish")
async def start_sel(message: Message):
    cats = await get_all_cat(message.from_user.id)
    keyboard = cat_keyboard(cats)
    await message.answer("Ko'chat sonini kiritmoqchi bo'lgan **Gruh**ni tanlang:", reply_markup=keyboard)
    await sel_state.c_id.set()


@dp.message_handler(state=sel_state.c_id)
async def select_category(message: Message, state: FSMContext):
    u_id = message.from_user.id
    c_name = (message.text or "").strip()

    c_id = await get_cat_id(u_id, c_name)

    if c_id:
        await state.update_data(c_id=int(c_id))

        # MUHIM: get_all_ty(u_id, c_id)
        types = await get_all_ty(u_id, int(c_id))
        keyboard = ty_keyboard(types)

        await message.answer(f"Tanlangan Gruh: **{c_name}**. Endi **Nav**ni tanlang:", reply_markup=keyboard)
        await sel_state.t_id.set()
    else:
        await message.answer("Iltimos, mavjud Gruh nomini tanlang.")


@dp.message_handler(state=sel_state.t_id)
async def select_type(message: Message, state: FSMContext):
    u_id = message.from_user.id
    t_name = (message.text or "").strip()

    data = await state.get_data()
    c_id = int(data["c_id"])

    # MUHIM: get_type_id(u_id, c_id, t_name)
    t_id = await get_type_id(u_id, c_id, t_name)

    if t_id:
        await state.update_data(t_id=int(t_id))
        await message.answer(
            "Iltimos, **1-sifat ko'chatlar sonini** kiriting (raqamda):",
            reply_markup=ReplyKeyboardRemove(),
        )
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


@dp.message_handler(state=sel_state.cuol_2)
async def add_q2(message: Message, state: FSMContext):
    try:
        q2 = int(message.text)
        await state.update_data(cuol_2=q2)
        await message.answer("Nihoyat, **3-sifat ko'chatlar sonini** kiriting (raqamda yoki 0):")
        await sel_state.cuol_3.set()
    except ValueError:
        await message.answer("Iltimos, son kiriting.")


@dp.message_handler(state=sel_state.cuol_3)
async def add_q3(message: Message, state: FSMContext):
    try:
        q3 = int(message.text)
        data = await state.get_data()
        u_id = message.from_user.id

        await new_seedling(
            u_id=int(u_id),
            t_id=int(data["t_id"]),
            q1=int(data["cuol_1"]),
            q2=int(data["cuol_2"]),
            q3=int(q3),
        )

        await message.answer("Ko'chatlar soni yangilandi!", reply_markup=main_manu)
        await state.finish()
    except ValueError:
        await message.answer("Iltimos, faqat son kiriting.")