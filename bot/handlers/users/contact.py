from aiogram import types
from loader import dp
from api_client import ensure_user
from keyboards.default.main_keyboards import main_manu


@dp.message_handler(content_types=types.ContentType.CONTACT)
async def on_contact(message: types.Message):
    # Faqat user o'z contactini yuborsa qabul qilamiz
    if not message.contact or message.contact.user_id != message.from_user.id:
        await message.answer("Faqat o'zingizning telefon raqamingizni yuboring.")
        return

    phone = message.contact.phone_number

    # backendda update (upsert)
    await ensure_user(
        u_id=message.from_user.id,
        u_name=message.from_user.full_name,
        u_username=message.from_user.username,
        u_phone=phone
    )

    await message.answer("Telefon raqamingiz saqlandi ✅ Endi davom etishingiz mumkin.", reply_markup=main_manu)