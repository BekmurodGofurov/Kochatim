from aiogram import types
from aiogram.dispatcher import FSMContext

from loader import dp
from api_client import partners_accept, partners_decline


def _kb(token: str):
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="✅ Ha, qabul qilaman", callback_data=f"partner_accept:{token}"),
        ],
        [
            types.InlineKeyboardButton(text="❌ Yo‘q", callback_data=f"partner_decline:{token}"),
        ],
    ])


@dp.callback_query_handler(lambda c: c.data and c.data.startswith("partner_accept:"))
async def cb_partner_accept(call: types.CallbackQuery, state: FSMContext):
    token = call.data.split(":", 1)[1]
    u_id = call.from_user.id
    try:
        res = await partners_accept(token=token, u_id=u_id)
        inviter_u_id = int(res.get("inviter_u_id"))
        invitee_u_id = int(res.get("invitee_u_id"))
        await call.message.edit_text("Hamkorlik taklifi qabul qilindi ✅")
        # notify both
        await dp.bot.send_message(inviter_u_id, f"✅ Sizning hamkorlik taklifingiz qabul qilindi.\nHamkor: `{invitee_u_id}`", parse_mode="Markdown")
        await dp.bot.send_message(invitee_u_id, f"✅ Siz hamkorlikni qabul qildingiz.\nHamkor: `{inviter_u_id}`", parse_mode="Markdown")
    except Exception:
        await call.message.edit_text("Xatolik: taklifni qabul qilib bo‘lmadi. Keyinroq urinib ko‘ring.")
    finally:
        await call.answer()


@dp.callback_query_handler(lambda c: c.data and c.data.startswith("partner_decline:"))
async def cb_partner_decline(call: types.CallbackQuery, state: FSMContext):
    token = call.data.split(":", 1)[1]
    u_id = call.from_user.id
    try:
        res = await partners_decline(token=token, u_id=u_id)
        inviter_u_id = int(res.get("inviter_u_id"))
        invitee_u_id = int(res.get("invitee_u_id"))
        await call.message.edit_text("Taklif rad etildi ❌")
        await dp.bot.send_message(inviter_u_id, f"❌ Sizning hamkorlik taklifingiz rad etildi.\nFoydalanuvchi: `{invitee_u_id}`", parse_mode="Markdown")
    except Exception:
        await call.message.edit_text("Xatolik: rad etib bo‘lmadi. Keyinroq urinib ko‘ring.")
    finally:
        await call.answer()

