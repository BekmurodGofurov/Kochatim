from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

media_links = InlineKeyboardMarkup(inline_keyboard=[
  [  
    InlineKeyboardButton(text="Telegram", callback_data="$telegram"),
    InlineKeyboardButton(text="Upwork", url="https://www.upwork.com/freelancers/~01a9dd82f01404fb42"),
  ],
  [
    InlineKeyboardButton(text="fiverr.", url="https://fiverr.com/users/bekmurod_0818/"),
    InlineKeyboardButton(text="Linkdin", url="https://www.linkedin.com/in/bekmurod-gofurov/")
  ],
  [
    InlineKeyboardButton(text="Tweeter", url="https://twitter.com/BekmurodGofurov"),
    InlineKeyboardButton(text="Facebook", url="https://www.facebook.com/bekmurod.dev")
  ],
  [
    InlineKeyboardButton(text="Instagram", callback_data="$instagram"),
    InlineKeyboardButton(text="LinkTree", url="https://linktr.ee/Bekmurod_/")
  ],
  [
    InlineKeyboardButton(text="Ko'proq", callback_data="$more_media"),
  ],
  [
    InlineKeyboardButton(text="Ortga qaytish🔙", callback_data="$backManu")
  ]
])

telegram_text =f"Mening shaxsiy Telegram kanallarim: "

telegram = InlineKeyboardMarkup(inline_keyboard=[
  [
    InlineKeyboardButton(text="Aosiy", url="https://t.me/Bekmurod_Gofurov"),
  ],
  [
    InlineKeyboardButton(text="Motivation", url="https://t.me/motivation_uzb_eng")
  ],
  [
    InlineKeyboardButton(text="Projects", url="https://t.me/bekmurod_programming_projects"),
  ],
  [
    InlineKeyboardButton(text="Musiqa", url="https://t.me/+16ZnYSCOC9cwODcy")
  ],
  [
    InlineKeyboardButton(text="Ortga qaytish🔙", callback_data="$backMadia")
  ]
])

other_text =f"Boshqa platformalar uchun linklar: "

other_links = InlineKeyboardMarkup(inline_keyboard=[
  [
    InlineKeyboardButton(text="Spotify", url="https://youtube.com/"),
  ],

  [
    InlineKeyboardButton(text="Pinterest", url="https://youtube.com/")
  ],

  [
    InlineKeyboardButton(text="Ortga qaytish 🔙", callback_data="$backMadia")
  ]
])

instagram_text = f"Instagram platformasida ikkita account dan foydalanaman bulat: Ommaviy va ish uchun."

instagram = InlineKeyboardMarkup(inline_keyboard=[
  [
    InlineKeyboardButton(text="Omaviy", url="https://www.instagram.com/2006_bekmurod/"),
  ],

  [
    InlineKeyboardButton(text="Ish uchun", url="https://www.instagram.com/bekmurod.dev/")
  ],

  [
    InlineKeyboardButton(text="Ortga qaytish 🔙", callback_data="$backMadia")
  ]
])