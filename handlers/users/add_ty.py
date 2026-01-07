from aiogram.types import Message, ReplyKeyboardRemove
from loader import dp
from aiogram.dispatcher import FSMContext
from states.state_one import type_state
from data.database import get_all_cat, get_cat_id, new_ty, get_a_ty, add_new_img
from keyboards.default.main_keyboards import cat_keyboard, new_tree
import datetime



@dp.message_handler(lambda message: message.text == "Yangi Nav")
async def cat_handler(message: Message):
    cat = get_all_cat(message.from_user.id)
    keyboard = cat_keyboard(cat)
    await message.answer(f"Iltimos quyda berilgan guruhlardan birini tanlang!", reply_markup=keyboard)
    await type_state.c_id.set()

@dp.message_handler(state=type_state.c_id)
async def add_cid(message: Message, state: FSMContext):
    text = message.text
    cats = get_all_cat(message.from_user.id)
    keyboard = cat_keyboard(cats)
    in_cat = False
    for cat in cats:
        if cat == text:
            in_cat = True
            break
    if in_cat:
        cat_id  = get_cat_id(message.from_user.id, text)
        await state.update_data(c_id=cat_id)
        await message.answer("Iltimos Nav nomini yuboring", reply_markup=ReplyKeyboardRemove())
        await type_state.t_name.set()

    else:
        await message.answer("Iltimos faqat sizdagi mavjud bo'lgan gruh nomini tanlang! ", reply_markup=keyboard)
        await type_state.c_id.set()

@dp.message_handler(state=type_state.t_name)
async def add_t_name(message: Message, state: FSMContext):
    text = message.text
    if get_a_ty(text, message.from_user.id):
        await state.update_data(t_name=text)
        await message.reply("Ushubu ko'chat navi haqida tafsilot bering: ", reply_markup=ReplyKeyboardRemove())
        await type_state.t_def.set()
    else:
        await message.answer(f"Siz yuborgan ko'chat navi allaqachon sizda mavjud!\n\nIltimos boshqa bir ko'chat navini kiriting!",reply_markup=ReplyKeyboardRemove())
        await type_state.t_name.set()


@dp.message_handler(state=type_state.t_def)
async def add_def(message: Message, state: FSMContext):
    await state.update_data(t_def=message.text)
    await message.answer("Endi ushbu nav uchun rasm yuboring:")
    await type_state.t_img.set()  # Rasm holatiga o'tamiz


@dp.message_handler(content_types=['photo'], state=type_state.t_img)
async def add_img(message: Message, state: FSMContext):
    data = await state.get_data()
    u_id = message.from_user.id
    photo_id = message.photo[-1].file_id

    # t_id endi bazadan qaytib keladi
    t_id = new_ty(
        c_id=data["c_id"],
        u_id=u_id,
        t_name=data["t_name"],
        deff=data["t_def"]
    )

    # Qaytib kelgan t_id orqali rasmni saqlaymiz
    add_new_img(t_id, photo_id)

    await message.answer("Yangi nav va rasm saqlandi!", reply_markup=new_tree)
    await state.finish()