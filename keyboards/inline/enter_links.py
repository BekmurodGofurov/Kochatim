from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

me_enter =f"Men haqimda malumot olish uchun, o'zingizga kerakli bo'lgan bo'limlardan birni tanlang!"

enterLinks = InlineKeyboardMarkup(inline_keyboard=[
  [
    InlineKeyboardButton(text="Ijtimoiy tarmoqlar 🔉", callback_data="$media"),
  ],
  [
    InlineKeyboardButton(text="Loyihalar 👨🏼‍💻", callback_data="$projects")
  ],
  [
    InlineKeyboardButton(text="Men Haimda 👤", callback_data="$me"),
  ],
])