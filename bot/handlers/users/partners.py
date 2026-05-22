from aiogram import types
from aiogram.dispatcher import FSMContext

from loader import dp
from api_client import partners_accept, partners_decline
from states.state_one import PartnerInviteState


def _kb():
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="✅ Ha, qabul qilaman", callback_data="pi_accept")],
        [types.InlineKeyboardButton(text="❌ Yo'q, kerak emas", callback_data="pi_decline")],
    ])


@dp.callback_query_handler(lambda c: c.data == "pi_accept", state=PartnerInviteState.pending)
async def cb_partner_accept(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    token = data.get("partner_token", "")
    await state.finish()
    try:
        res = await partners_accept(token=token, u_id=call.from_user.id)
        inviter_u_id = int(res["inviter_u_id"])
        invitee_name = call.from_user.full_name
        await call.message.edit_text("✅ Hamkorlik taklifi qabul qilindi!")
        await dp.bot.send_message(
            inviter_u_id,
            f"✅ *{invitee_name}* hamkorlik taklifingizni qabul qildi!",
            parse_mode="Markdown",
        )
    except Exception:
        await call.message.edit_text("❌ Xatolik yuz berdi. Keyinroq urinib ko'ring.")
    finally:
        await call.answer()


@dp.callback_query_handler(lambda c: c.data == "pi_decline", state=PartnerInviteState.pending)
async def cb_partner_decline(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    token = data.get("partner_token", "")
    await state.finish()
    try:
        res = await partners_decline(token=token, u_id=call.from_user.id)
        inviter_u_id = int(res["inviter_u_id"])
        invitee_name = call.from_user.full_name
        await call.message.edit_text("❌ Taklif rad etildi.")
        await dp.bot.send_message(
            inviter_u_id,
            f"❌ *{invitee_name}* hamkorlik taklifingizni rad etdi.",
            parse_mode="Markdown",
        )
    except Exception:
        await call.message.edit_text("❌ Xatolik yuz berdi. Keyinroq urinib ko'ring.")
    finally:
        await call.answer()
