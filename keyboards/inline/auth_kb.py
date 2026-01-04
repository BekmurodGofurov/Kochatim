from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton



cancel_kb = InlineKeyboardMarkup(inline_keyboard=[
  [
    InlineKeyboardButton(text="Bekor qilsih ❌", callback_data="$cancel")
  ]
])

finsh_kb = InlineKeyboardMarkup(inline_keyboard=[
  [
    InlineKeyboardButton(text="Bekor qilsih ❌", callback_data="$cancel")
  ],
  [
    InlineKeyboardButton(text="Tasdiqlash ✅", callback_data="$done")
  ]
])

registor = InlineKeyboardMarkup(inline_keyboard=[
  [
    InlineKeyboardButton(text="Roʻyxatdan oʻtish🪪", callback_data="$auth")
  ]
])




