import time
from aiogram import types
from aiogram.dispatcher.filters.builtin import CommandStart

from loader import dp
from api_client import ensure_user, get_user
from keyboards.default.main_keyboards import contact_kb, main_manu


@dp.message_handler(CommandStart())
async def bot_start(message: types.Message):
    t0 = time.perf_counter()

    u = message.from_user

    # 1) backendda user borligini ta'minlash (phone bo'lmasa ham)
    t1 = time.perf_counter()
    await ensure_user(
        u_id=u.id,
        u_name=u.full_name,
        u_username=u.username
    )
    print(f"[START] ensure_user {(time.perf_counter() - t1) * 1000:.0f}ms")

    # 2) user ma'lumotini olib, phone bor-yo'qligini tekshirish
    t2 = time.perf_counter()
    user_row = await get_user(u.id)
    print(f"[START] get_user {(time.perf_counter() - t2) * 1000:.0f}ms")

    phone = user_row.get("u_phone")

    if not phone:
        await message.answer(
            "Davom etish uchun telefon raqamingizni yuboring (Contact).",
            reply_markup=contact_kb
        )
        print(f"[START] total {(time.perf_counter() - t0) * 1000:.0f}ms (need phone)")
        return

    await message.answer("Xush kelibsiz. Ma'lumotlaringiz mavjud ✅", reply_markup=main_manu)
    print(f"[START] total {(time.perf_counter() - t0) * 1000:.0f}ms (ok)")