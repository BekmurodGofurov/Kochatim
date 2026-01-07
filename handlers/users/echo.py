from aiogram.types import Message, ReplyKeyboardRemove
from loader import dp
from data.database import get_all_cat, get_all_ty,get_cat_id, get_type_info, get_type_id, get_seedling_count,get_img_url
from keyboards.default.main_keyboards import ty_keyboard

@dp.message_handler(state=None)
async def bot_echo(message: Message):
    u_id = message.from_user.id
    text = message.text

    cats = get_all_cat(u_id)
    if text in cats:
        c_id = get_cat_id(u_id, text)
        ty = get_all_ty(c_id, u_id)
        n= len(ty)
        keyboard = ty_keyboard(ty)
        await message.answer(f"Sizdagi <b>'{text}'</b> gurhga tegizli valar <b>{n}ta</b>", reply_markup=keyboard)
        return


    t_id = None
    for c_name in cats:
        c_id = get_cat_id(u_id, c_name)
        current_t_id = get_type_id(c_id, u_id, text)
        if current_t_id:
            t_id = current_t_id
            break

    if t_id:
        t_info = get_type_info(t_id)
        photo_url = get_img_url(t_id)

        if t_info:
            t_name, t_deff = t_info
        else:
            t_name, t_deff = text, "Tafsilotlar topilmadi."

        sonlar = get_seedling_count(t_id)
        umumiy_son = sonlar['sifat_1'] + sonlar['sifat_2'] + sonlar['sifat_3']

        xabar = f"🌳 <b>{t_name} Navining to'liq ma'lumoti:</b>\n\n"
        if umumiy_son > 0:
            xabar += "📦 <b>Inventar soni:</b>\n"
            if sonlar['sifat_1'] > 0:
                xabar += f"🥇 1-sifat ko'chatlar soni: <b>{sonlar['sifat_1']}</b> ta\n"
            if sonlar['sifat_2'] > 0:
                xabar += f"🥈 2-sifat ko'chatlar soni: <b>{sonlar['sifat_2']}</b> ta\n"
            if sonlar['sifat_3'] > 0:
                xabar += f"🥉 3-sifat ko'chatlar soni: <b>{sonlar['sifat_3']}</b> ta\n"
            xabar += f"\nJami inventar: <b>{umumiy_son}</b> ta\n"
        else:
            xabar += "📦 Inventar: Hozircha bu navda ko'chat qo'shilmagan.\n"

        xabar += f"\n📝 <b>Tavsif:</b>\n{t_deff}"

        if photo_url:
            await message.answer_photo(photo=photo_url, caption=xabar)
        else:
            await message.answer(xabar)
        return
    await message.answer(f"Afsuski, siz yubotgan <b>'{text}'</b> haqida bizda hech qanday ma'lumot yo'q.")