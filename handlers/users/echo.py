from aiogram.types import Message, ReplyKeyboardRemove
from loader import dp
from data.database import get_all_cat, get_all_ty,get_cat_id, get_type_info, get_type_id, get_seedling_count
from keyboards.default.main_keyboards import ty_keyboard

@dp.message_handler(state=None)
async def bot_echo(message: Message):
    u_id = message.from_user.id
    text = message.text

    cats = get_all_cat(u_id)
    if text in cats:
        c_id = get_cat_id(u_id, text)
        ty = get_all_ty(c_id, u_id)
        keyboard = ty_keyboard(ty)
        await message.answer(f"Sizdagi '{text}' Gruhiga tegishli navlar:", reply_markup=keyboard)
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
        if t_info:
            t_name, t_deff = t_info
        else:
            t_name, t_deff = text, "Tafsilotlar topilmadi."

        sonlar = get_seedling_count(t_id)

        xabar = f"🌳 **{t_name} Navining to'liq ma'lumoti:**\n\n"

        umumiy_son = sonlar['sifat_1'] + sonlar['sifat_2'] + sonlar['sifat_3']

        if umumiy_son > 0:
            xabar += "📦 **Inventar soni:**\n"
            if sonlar['sifat_1'] > 0:
                xabar += f"🥇 1-sifat ko'chatlar soni: **{sonlar['sifat_1']} ta**\n"
            if sonlar['sifat_2'] > 0:
                xabar += f"🥈 2-sifat ko'chatlar soni: **{sonlar['sifat_2']} ta**\n"
            if sonlar['sifat_3'] > 0:
                xabar += f"🥉 3-sifat ko'chatlar soni: **{sonlar['sifat_3']} ta**\n"
            xabar += f"\n**Jami inventar:** {umumiy_son} ta\n"
        else:
            xabar += "📦 **Inventar:** Hozircha bu navda ko'chat qo'shilmagan.\n"

        xabar += f"\n📝 **Nav tavsifi:**\n{t_deff}"
        await message.answer(xabar, reply_markup=ReplyKeyboardRemove())

        return
    await message.answer(f"Afsuski, siz yubotgan '{text}' haqida bizda hech qanday ma'lumot yo'q.")