from aiogram.types import ReplyKeyboardMarkup, KeyboardButton # type: ignore

channel_list = ReplyKeyboardMarkup(one_time_keyboard=True, keyboard=[
  [
    KeyboardButton(text="@Bekmurod_Gofurov"),
    KeyboardButton(text="@bekmuord_music")
  ],

  [
    KeyboardButton(text="@motivation_uzb_eng"),
    KeyboardButton(text="@bekmurod_programming_projects")
  ],

  [
    KeyboardButton(text="Cancel ❌")
  ],
], resize_keyboard=True)
