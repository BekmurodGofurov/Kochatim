import time
from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.builtin import CommandStart

from loader import dp
from api_client import ensure_user
from data.database import get_all_cat, get_all_types_for_user
from keyboards.default.main_keyboards import contact_kb, get_main_menu
from states.state_one import PartnerInviteState
from .partners import _kb as partner_invite_kb


@dp.message_handler(CommandStart())
async def bot_start(message: types.Message, state: FSMContext):
    t0 = time.perf_counter()

    u = message.from_user

    u_photo = None
    try:
        photos = await u.get_profile_photos(limit=1)
        if photos and photos.total_count > 0:
            u_photo = photos.photos[0][-1].file_id
    except Exception as e:
        print(f"[START] photo error: {e}")

    t1 = time.perf_counter()
    user_row = await ensure_user(
        u_id=u.id,
        u_name=u.full_name,
        u_username=u.username,
        u_photo=u_photo,
    )
    print(f"[START] ensure_user {(time.perf_counter() - t1) * 1000:.0f}ms")

    phone = user_row.get("u_phone")

    # Deep-link tekshiruvi — phone gate DAN OLDIN
    partner_token = None
    args = message.get_args().strip()
    print(f"[START] args raw={repr(args)} len={len(args)}")
    if args.startswith("partner_"):
        partner_token = args[len("partner_"):]

    if not phone:
        if partner_token:
            # Tokenni saqlaymiz, telefon olgandan keyin ko'rsatamiz
            await state.update_data(partner_token=partner_token)
        await message.answer(
            "Davom etish uchun telefon raqamingizni yuboring (Contact).",
            reply_markup=contact_kb,
        )
        print(f"[START] total {(time.perf_counter() - t0) * 1000:.0f}ms (need phone)")
        return

    if partner_token:
        await state.update_data(partner_token=partner_token)
        await PartnerInviteState.pending.set()
        await message.answer(
            "Sizni hamkorlikka chaqirishdi.\n\nQabul qilasizmi?",
            reply_markup=partner_invite_kb(),
        )
        print(f"[START] total {(time.perf_counter() - t0) * 1000:.0f}ms (partner invite)")
        return

    cats = await get_all_cat(u.id)
    types_list = await get_all_types_for_user(u.id)
    markup = get_main_menu(has_cats=bool(cats), has_types=bool(types_list))

    await message.answer("Xush kelibsiz. Ma'lumotlaringiz mavjud ✅", reply_markup=markup)
    print(f"[START] total {(time.perf_counter() - t0) * 1000:.0f}ms (ok)")
