from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

project_text =f"Siz mening loyihalarimni Telegram kanalimdan va GitHup dan ko'rishingiz va foydalanib ko'rishingiz mumkun"

project = InlineKeyboardMarkup(inline_keyboard=[
  [
    InlineKeyboardButton(text="GitHub", url="https://github.com/BekmurodGofurov"),
  ],
  [
    InlineKeyboardButton(text="Telegram", url="https://t.me/bekmurod_programming_projects")
  ],
  [
    InlineKeyboardButton(text="Ortga qaytish 🔙", callback_data="$backManu")
  ]

])

backmeedia01 = InlineKeyboardMarkup(inline_keyboard=[
  [
    InlineKeyboardButton(text="Ortga qaytish 🔙", callback_data="$backManu")
  ]
])