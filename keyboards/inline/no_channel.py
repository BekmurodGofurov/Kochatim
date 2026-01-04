from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


isnot_member = InlineKeyboardMarkup(inline_keyboard=[
  [  
    InlineKeyboardButton(text="Knalaga obuna bo'lish", url='https://t.me/Bekmurod_Gofurov'),
  ],
  [
    InlineKeyboardButton(text='Tekshirish', callback_data='$check_channel')
  ]
])

start_chat = InlineKeyboardMarkup(inline_keyboard=[
  [
    InlineKeyboardButton(text="Xabar yuborishni boshlash💬", callback_data='$start_caht')
  ],  
  [
    InlineKeyboardButton(text="Hozir emas🚫", callback_data='$busy')
  ]
])

start_bot_chat = InlineKeyboardMarkup(inline_keyboard=[
  [
    InlineKeyboardButton(text="Xabar yuborishni boshlash💬", callback_data='$botstart_caht')
  ],  
  [
    InlineKeyboardButton(text="Hozir emas🚫", callback_data='$busy')
  ]
])

accept = InlineKeyboardMarkup(inline_keyboard=[
   [
    InlineKeyboardButton(text="Bekor qilsih ❌", callback_data="$cancel")
  ],
  [
    InlineKeyboardButton(text="Yuborish 📤", callback_data='$send_admin')
  ],  
  
])

accept_bot = InlineKeyboardMarkup(inline_keyboard=[
   [
    InlineKeyboardButton(text="Bekor qilsih ❌", callback_data="$cancel")
  ],
  [
    InlineKeyboardButton(text="Yuborish 📤", callback_data='$send_admin_about_bot')
  ],  
  
])