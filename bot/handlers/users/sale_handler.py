from aiogram.types import Message, ReplyKeyboardRemove
from loader import dp
from aiogram.dispatcher import FSMContext
from states.state_one import sale_state
from data.database import get_all_cat, get_cat_id, get_all_ty, get_type_id, add_sale
from keyboards.default.main_keyboards import cat_keyboard, ty_keyboard, main_manu


@dp.message_handler(text="Sotuv")
async def start_sale(message: Message):
    cats = await get_all_cat(message.from_user.id)
    if not cats:
        await message.answer("Sizda hali guruhlar yo'q.")
        return
    await message.answer("Qaysi guruhdan sotuv bo'ldi?", reply_markup=cat_keyboard(cats))
    await sale_state.c_id.set()


@dp.message_handler(state=sale_state.c_id)
async def sale_cat(message: Message, state: FSMContext):
    c_id = await get_cat_id(message.from_user.id, message.text)
    if c_id:
        await state.update_data(c_id=c_id)
        ty = await get_all_ty(message.from_user.id, int(c_id))  
        keyboard = ty_keyboard(ty) if ty else None
        await message.answer("Navni tanlang:", reply_markup=keyboard)
        await sale_state.t_id.set()
    else:
        await message.answer("Xato guruh. Tanlang:")


@dp.message_handler(state=sale_state.t_id)
async def sale_type(message: Message, state: FSMContext):
    data = await state.get_data()
    t_id = await get_type_id(message.from_user.id, data['c_id'], message.text)
    if t_id:
        await state.update_data(t_id=t_id)
        await message.answer("1-navdan necha dona sotildi?", reply_markup=ReplyKeyboardRemove())
        await sale_state.q1.set()
    else:
        await message.answer("Navni to'g'ri tanlang.")


@dp.message_handler(state=sale_state.q1)
async def sale_q1(message: Message, state: FSMContext):
    await state.update_data(q1=int(message.text))
    await message.answer("2-navdan necha dona sotildi?")
    await sale_state.q2.set()


@dp.message_handler(state=sale_state.q2)
async def sale_q2(message: Message, state: FSMContext):
    await state.update_data(q2=int(message.text))
    await message.answer("3-navdan necha dona sotildi?")
    await sale_state.q3.set()


@dp.message_handler(state=sale_state.q3)
async def sale_q3(message: Message, state: FSMContext):
    await state.update_data(q3=int(message.text))
    await message.answer("Umumiy qanchaga sotildi (narxi)?")
    await sale_state.price.set()


@dp.message_handler(state=sale_state.price)
async def sale_final(message: Message, state: FSMContext):
    try:
        price = float(message.text)
        data = await state.get_data()

        success = await add_sale(
            message.from_user.id, data['c_id'], data['t_id'],
            data['q1'], data['q2'], data['q3'], price
        )

        if success:
            await message.answer(f"Sotuv muvaffaqiyatli qayd etildi!\nJami: {price} so'm", reply_markup=main_manu)
        else:
            await message.answer("Xatolik yuz berdi.", reply_markup=main_manu)
        await state.finish()
    except ValueError:
        await message.answer("Narxni faqat raqamda kiriting.")