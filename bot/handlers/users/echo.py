from aiogram.types import Message
from loader import dp

from data.database import (
    get_all_cat,
    get_all_ty,
    get_cat_id,
    get_type_info,
    get_type_id,
    get_seedling_count,
    get_img_url,
    get_all_types_for_user,
)
from keyboards.default.main_keyboards import ty_keyboard, main_manu


@dp.message_handler(state=None)
async def bot_echo(message: Message):
    u_id = message.from_user.id
    text = (message.text or "").strip()

    cats = await get_all_cat(u_id) 

    if text in cats:
        c_id = await get_cat_id(u_id, text)
        if not c_id:
            await message.answer(f"Guruh topilmadi: <b>{text}</b>")
            return

        ty = await get_all_ty(u_id, int(c_id))  
        n = len(ty)

        keyboard = ty_keyboard(ty) if ty else None
        await message.answer(
            f"Sizdagi <b>'{text}'</b> guruhga tegishli navlar: <b>{n}ta</b>",
            reply_markup=keyboard,
        )
        return

    # 2) TYPE QIDIRISH (user nav nomini yozsa -> qaysi categoryda borligini topamiz)
    all_types = await get_all_types_for_user(u_id)
    t_id = None
    
    # Kiritilgan textga mos navni qidiramiz
    search_text = text.lower().strip()
    for ty in all_types:
        if ty.get("t_name", "").lower().strip() == search_text:
            t_id = int(ty["t_id"])
            break

    if not t_id:
        await message.answer(
            f"Afsuski, siz yuborgan <b>'{text}'</b> haqida bizda hech qanday ma'lumot yo'q."
        )
        return

    # 3) TYPE INFO + INVENTAR + RASM
    # MUHIM: get_type_info(u_id, t_id) bo'lishi kerak
    t_info = await get_type_info(u_id, t_id)  # dict bo'lishi kerak
    photo_url = await get_img_url(t_id)  # str yoki None

    # t_info dict bo'lsa:
    if isinstance(t_info, dict):
        t_name = (t_info.get("t_name") or text).strip()
        t_deff = (t_info.get("deff") or "Tafsilotlar topilmadi.").strip()
    else:
        # fallback (agar backend boshqa format qaytarsa)
        t_name = text
        t_deff = "Tafsilotlar topilmadi."

    # MUHIM: get_seedling_count(u_id, t_id)
    sonlar = await get_seedling_count(u_id, t_id) or {}

    # MUHIM: key nomlari quality_1/2/3
    q1 = int(sonlar.get("quality_1") or 0)
    q2 = int(sonlar.get("quality_2") or 0)
    q3 = int(sonlar.get("quality_3") or 0)
    umumiy_son = q1 + q2 + q3

    xabar = f"🌳 <b>{t_name} navining to'liq ma'lumoti:</b>\n\n"
    if umumiy_son > 0:
        xabar += "📦 <b>Inventar soni:</b>\n"
        if q1 > 0:
            xabar += f"🥇 1-sifat: <b>{q1}</b> ta\n"
        if q2 > 0:
            xabar += f"🥈 2-sifat: <b>{q2}</b> ta\n"
        if q3 > 0:
            xabar += f"🥉 3-sifat: <b>{q3}</b> ta\n"
        xabar += f"\nJami: <b>{umumiy_son}</b> ta\n"
    else:
        xabar += "📦 Inventar: Hozircha bu navda ko'chat qo'shilmagan.\n"

    xabar += f"\n📝 <b>Tavsif:</b>\n{t_deff}"

    if photo_url:
        await message.answer_photo(photo=photo_url, caption=xabar, reply_markup=main_manu)
    else:
        await message.answer(xabar, reply_markup=main_manu)