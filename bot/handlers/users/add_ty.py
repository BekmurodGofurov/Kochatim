from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

from loader import dp
from data.database import get_all_cat, get_cat_id, new_ty, add_new_img
from keyboards.default.main_keyboards import cat_keyboard, main_manu


ST_ADD_TY_CAT = "add_ty:cat"
ST_ADD_TY_NAME = "add_ty:name"
ST_ADD_TY_DEFF = "add_ty:deff"
ST_ADD_TY_IMG = "add_ty:img"

@dp.message_handler(Text(equals="Yangi Nav"), state="*")
async def add_ty_start(message: types.Message, state: FSMContext):
    await state.finish()
    u_id = message.from_user.id

    cats = await get_all_cat(u_id)  # LIST[str]
    if not cats:
        await message.answer("Sizda hali guruh yo‘q. Avval 'Yangi Guruh' qo‘shing.", reply_markup=main_manu)
        return

    await message.answer("Iltimos guruhlardan birini tanlang:", reply_markup=cat_keyboard(cats))
    await state.set_state(ST_ADD_TY_CAT)


@dp.message_handler(state=ST_ADD_TY_CAT)
async def add_ty_pick_cat(message: types.Message, state: FSMContext):
    u_id = message.from_user.id
    c_name = (message.text or "").strip()

    cats = await get_all_cat(u_id)
    if c_name not in cats:
        await message.answer(
            "Iltimos faqat sizdagi mavjud bo‘lgan guruh nomini tanlang!",
            reply_markup=cat_keyboard(cats),
        )
        return

    c_id = await get_cat_id(u_id, c_name)
    if not c_id:
        await message.answer("Guruh topilmadi. Qaytadan urinib ko‘ring.", reply_markup=main_manu)
        await state.finish()
        return

    await state.update_data(c_id=int(c_id), c_name=c_name)
    await message.answer("Yangi nav nomini yuboring (matn).",reply_markup=ReplyKeyboardRemove())
    await state.set_state(ST_ADD_TY_NAME)


@dp.message_handler(state=ST_ADD_TY_NAME, content_types=types.ContentType.TEXT)
async def add_ty_name(message: types.Message, state: FSMContext):
    t_name = (message.text or "").strip()
    if not t_name:
        await message.answer("Nav nomi bo‘sh bo‘lmasin. Qayta yuboring.")
        return

    await state.update_data(t_name=t_name)
    await message.answer("Ko'chat haqida malumot qoldiring!")
    await state.set_state(ST_ADD_TY_DEFF)


@dp.message_handler(state=ST_ADD_TY_DEFF, content_types=types.ContentType.TEXT)
async def add_ty_deff(message: types.Message, state: FSMContext):
    txt = (message.text or "").strip()

    deff = None if txt == "⏭ O‘tkazib yuborish" else (txt or None)

    data = await state.get_data()
    u_id = message.from_user.id
    c_id = data.get("c_id")
    t_name = data.get("t_name")

    if not c_id or not t_name:
        await message.answer("Xatolik. Qaytadan boshlang.", reply_markup=main_manu)
        await state.finish()
        return

    created = await new_ty(u_id=int(u_id), c_id=int(c_id), t_name=t_name, deff=deff)

    # backend javobidan t_id ni olish
    t_id = None
    if isinstance(created, dict):
        if created.get("t_id") is not None:
            t_id = created.get("t_id")
        elif isinstance(created.get("type"), dict) and created["type"].get("t_id") is not None:
            t_id = created["type"].get("t_id")

    if not t_id:
        await message.answer("Nav yaratildi, lekin t_id topilmadi. Backend javobini tekshiring.", reply_markup=main_manu)
        await state.finish()
        return

    await state.update_data(t_id=int(t_id))
    await message.answer("Nav yaratildi ✅ Endi rasm yuboring (photo).", reply_markup=ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton("⬅️ Orqaga")]],
        resize_keyboard=True
    ))
    await state.set_state(ST_ADD_TY_IMG)


@dp.message_handler(state=ST_ADD_TY_IMG, content_types=types.ContentType.PHOTO)
async def add_ty_add_img(message: types.Message, state: FSMContext):
    data = await state.get_data()
    t_id = data.get("t_id")
    if not t_id:
        await message.answer("Xatolik. Qaytadan boshlang.", reply_markup=main_manu)
        await state.finish()
        return

    photo_id = message.photo[-1].file_id
    await add_new_img(int(t_id), photo_id)

    await message.answer("Rasm saqlandi ✅", reply_markup=main_manu)
    await state.finish()


@dp.message_handler(state=ST_ADD_TY_IMG)
async def add_ty_need_photo(message: types.Message, state: FSMContext):
    await message.answer("Iltimos rasm yuboring (photo).")