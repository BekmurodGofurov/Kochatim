from aiogram import types
from aiogram.dispatcher import FSMContext
from loader import dp
from data.database import get_all_cat_rows, get_all_ty_rows, update_cat, delete_cat, update_ty, delete_ty
from keyboards.default.main_keyboards import manage_cat_inline, manage_ty_inline, delete_confirm_inline, main_manu
from states.state_one import manage_cat_state, manage_ty_state

@dp.message_handler(text="Boshqaruv")
async def start_management(message: types.Message):
    await message.answer("Nimanı boshqarmoqchisiz?", reply_markup=types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton("Guruhlarni boshqarish")],
            [types.KeyboardButton("Navlarni boshqarish")],
            [types.KeyboardButton("Asosiy menu")]
        ],
        resize_keyboard=True
    ))

@dp.message_handler(text="Asosiy menu")
async def back_to_main(message: types.Message):
    await message.answer("Asosiy menu", reply_markup=main_manu)

# ================= CATEGORY MANAGEMENT =================

@dp.message_handler(text="Guruhlarni boshqarish")
async def manage_categories(message: types.Message):
    cats = await get_all_cat_rows(message.from_user.id)
    if not cats:
        await message.answer("Sizda hali guruhlar yo'q.")
        return
    
    for cat in cats:
        await message.answer(f"Guruh: {cat['c_name']}", reply_markup=manage_cat_inline(cat['c_id']))

@dp.callback_query_handler(lambda c: c.data.startswith('edit_cat:'))
async def edit_category_start(callback_query: types.CallbackQuery, state: FSMContext):
    c_id = int(callback_query.data.split(':')[1])
    await manage_cat_state.c_id.set()
    await state.update_data(c_id=c_id)
    await manage_cat_state.c_name.set()
    await callback_query.message.answer("Guruh uchun yangi nom kiriting:")
    await callback_query.answer()

@dp.message_handler(state=manage_cat_state.c_name)
async def edit_category_finish(message: types.Message, state: FSMContext):
    data = await state.get_data()
    c_id = data['c_id']
    new_name = message.text.strip()
    
    res = await update_cat(message.from_user.id, c_id, new_name)
    if res:
        await message.answer(f"Guruh nomi '{new_name}' ga o'zgartirildi ✅", reply_markup=main_manu)
    else:
        await message.answer("Xatolik yuz berdi ❌")
    await state.finish()

@dp.callback_query_handler(lambda c: c.data.startswith('delete_cat:'))
async def delete_category_start(callback_query: types.CallbackQuery):
    c_id = int(callback_query.data.split(':')[1])
    await callback_query.message.answer("Haqiqatan ham ushbu guruhni o'chirmoqchimisiz?", 
                                         reply_markup=delete_confirm_inline("cat", c_id))
    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data.startswith('conf_del_cat:'))
async def delete_category_finish(callback_query: types.CallbackQuery):
    c_id = int(callback_query.data.split(':')[1])
    res = await delete_cat(callback_query.from_user.id, c_id)
    if res:
        await callback_query.message.edit_text("Guruh o'chirildi ✅")
    else:
        await callback_query.message.edit_text("Xatolik yuz berdi ❌ (Balki bu guruhda navlar bordir?)")
    await callback_query.answer()

# ================= TYPE MANAGEMENT =================

@dp.message_handler(text="Navlarni boshqarish")
async def choose_cat_for_types(message: types.Message):
    cats = await get_all_cat_rows(message.from_user.id)
    if not cats:
        await message.answer("Sizda hali guruhlar yo'q.")
        return
    
    kb = types.InlineKeyboardMarkup()
    for cat in cats:
        kb.add(types.InlineKeyboardButton(text=cat['c_name'], callback_data=f"manage_ty_in_cat:{cat['c_id']}"))
    
    await message.answer("Qaysi guruhning navlarini boshqarmoqchisiz?", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith('manage_ty_in_cat:'))
async def list_types_to_manage(callback_query: types.CallbackQuery):
    c_id = int(callback_query.data.split(':')[1])
    types_list = await get_all_ty_rows(callback_query.from_user.id, c_id)
    
    if not types_list:
        await callback_query.message.answer("Ushbu guruhda navlar yo'q.")
    else:
        for ty in types_list:
            text = f"Nav: {ty['t_name']}\nTavsif: {ty.get('deff') or 'Yo`q'}"
            await callback_query.message.answer(text, reply_markup=manage_ty_inline(ty['t_id']))
    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data.startswith('edit_ty:'))
async def edit_type_start(callback_query: types.CallbackQuery, state: FSMContext):
    t_id = int(callback_query.data.split(':')[1])
    await manage_ty_state.t_id.set()
    await state.update_data(t_id=t_id)
    await manage_ty_state.t_name.set()
    await callback_query.message.answer("Nav uchun yangi nom kiriting:")
    await callback_query.answer()

@dp.message_handler(state=manage_ty_state.t_name)
async def edit_type_name(message: types.Message, state: FSMContext):
    await state.update_data(t_name=message.text.strip())
    await manage_ty_state.t_def.set()
    await message.answer("Yangi tavsif kiriting (yoki /skip):")

@dp.message_handler(state=manage_ty_state.t_def)
async def edit_type_finish(message: types.Message, state: FSMContext):
    data = await state.get_data()
    t_id = data['t_id']
    t_name = data['t_name']
    t_def = message.text.strip()
    if t_def == "/skip":
        t_def = None
    
    res = await update_ty(message.from_user.id, t_id, t_name, t_def)
    if res:
        await message.answer(f"Nav '{t_name}' muvaffaqiyatli yangilandi ✅", reply_markup=main_manu)
    else:
        await message.answer("Xatolik yuz berdi ❌")
    await state.finish()

@dp.callback_query_handler(lambda c: c.data.startswith('delete_ty:'))
async def delete_type_start(callback_query: types.CallbackQuery):
    t_id = int(callback_query.data.split(':')[1])
    await callback_query.message.answer("Haqiqatan ham ushbu navni o'chirmoqchimisiz?", 
                                         reply_markup=delete_confirm_inline("ty", t_id))
    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data.startswith('conf_del_ty:'))
async def delete_type_finish(callback_query: types.CallbackQuery):
    t_id = int(callback_query.data.split(':')[1])
    res = await delete_ty(callback_query.from_user.id, t_id)
    if res:
        await callback_query.message.edit_text("Nav o'chirildi ✅")
    else:
        await callback_query.message.edit_text("Xatolik yuz berdi ❌")
    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data == 'cancel_del')
async def cancel_delete(callback_query: types.CallbackQuery):
    await callback_query.message.edit_text("O'chirish bekor qilindi.")
    await callback_query.answer()
