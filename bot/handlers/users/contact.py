from aiogram import types
from aiogram.dispatcher import FSMContext

from loader import dp
from api_client import ensure_user
from data.database import get_all_cat, get_all_types_for_user
from keyboards.default.main_keyboards import get_main_menu
from states.state_one import PartnerInviteState
from .partners import _kb as partner_invite_kb


@dp.message_handler(content_types=types.ContentType.CONTACT, state="*")
async def on_contact(message: types.Message, state: FSMContext):
    if not message.contact or message.contact.user_id != message.from_user.id:
        await message.answer("Faqat o'zingizning telefon raqamingizni yuboring.")
        return

    phone = message.contact.phone_number

    await ensure_user(
        u_id=message.from_user.id,
        u_name=message.from_user.full_name,
        u_username=message.from_user.username,
        u_phone=phone,
    )

    # Pending partner invite bormi?
    data = await state.get_data()
    partner_token = data.get("partner_token")
    if partner_token:
        await PartnerInviteState.pending.set()
        await message.answer(
            "Telefon raqamingiz saqlandi ✅\n\nSizni hamkorlikka chaqirishdi.\n\nQabul qilasizmi?",
            reply_markup=partner_invite_kb(),
        )
        return

    await state.finish()

    cats = await get_all_cat(message.from_user.id)
    types_list = await get_all_types_for_user(message.from_user.id)
    markup = get_main_menu(has_cats=bool(cats), has_types=bool(types_list))

    await message.answer("Telefon raqamingiz saqlandi ✅ Endi davom etishingiz mumkin.", reply_markup=markup)
