from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def cat_keyboard(arr):
    categories_keyboard = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    new_cat_button = KeyboardButton(text="Yangi Gruh")
    for name in arr:
        categories_keyboard.insert(KeyboardButton(text=name))
    categories_keyboard.row(new_cat_button)
    return categories_keyboard

def ty_keyboard(arr):
    types_keyboard = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    new_cat_button = KeyboardButton(text="Yangi Nav")
    for name in arr:
        types_keyboard.insert(KeyboardButton(text=name))
    types_keyboard.row(new_cat_button)
    return types_keyboard

new_tree = ReplyKeyboardMarkup(one_time_keyboard=True, keyboard=[
  [
    KeyboardButton(text="Ko'chat Qo'shish"),
  ]
], resize_keyboard=True)

main_manu = ReplyKeyboardMarkup(one_time_keyboard=True, keyboard=[
  [
      KeyboardButton(text="Yangi Gruh"),
      KeyboardButton(text="Yangi Nav"),
  ],
  [
      KeyboardButton(text="Gruh"),
      KeyboardButton(text="Ko'chat Qo'shish"),
  ],
  [
      KeyboardButton(text="Sotish"),
  ],
], resize_keyboard=True)