from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


helpKeys = InlineKeyboardMarkup(inline_keyboard=[
    [
      InlineKeyboardButton(text="Callback data", callback_data="$cb-data")
    ],
    [
      InlineKeyboardButton(text="URL", url="https://youtube.com/")
    ],
    [
      InlineKeyboardButton(text="Search", switch_inline_query_current_chat=""),
      InlineKeyboardButton(text="Share", switch_inline_query="Tavsiya qilaman!")
    ]
])