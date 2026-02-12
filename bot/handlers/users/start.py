import time
from aiogram import types
from aiogram.dispatcher.filters.builtin import CommandStart

from loader import dp
from api_client import ensure_user, get_user
from data.database import get_all_cat, get_all_types_for_user
from keyboards.default.main_keyboards import contact_kb, get_main_menu


@dp.message_handler(CommandStart())
async def bot_start(message: types.Message):
    t0 = time.perf_counter()

    u = message.from_user

    u_photo = None
    try:
        photos = await u.get_profile_photos(limit=1)
        if photos and photos.total_count > 0:
            # eng kattasini olamiz (-1)
            u_photo = photos.photos[0][-1].file_id
    except Exception as e:
        print(f"[START] photo error: {e}")

    # 1) backendga yuborish
    t1 = time.perf_counter()
    # ensure_user returns the user row, so we don't necessarily need a separate get_user
    user_row = await ensure_user(
        u_id=u.id,
        u_name=u.full_name,
        u_username=u.username,
        u_photo=u_photo
    )
    print(f"[START] ensure_user {(time.perf_counter() - t1) * 1000:.0f}ms")

    phone = user_row.get("u_phone")

    if not phone:
        await message.answer(
            "Davom etish uchun telefon raqamingizni yuboring (Contact).",
            reply_markup=contact_kb
        )
        print(f"[START] total {(time.perf_counter() - t0) * 1000:.0f}ms (need phone)")
        return

    # 3) Dinamik menu
    cats = await get_all_cat(u.id)
    types_list = await get_all_types_for_user(u.id)
    markup = get_main_menu(has_cats=bool(cats), has_types=bool(types_list))

    await message.answer("Xush kelibsiz. Ma'lumotlaringiz mavjud ✅", reply_markup=markup)
    print(f"[START] total {(time.perf_counter() - t0) * 1000:.0f}ms (ok)")