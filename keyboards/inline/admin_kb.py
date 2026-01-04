from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


home_ad = InlineKeyboardMarkup(inline_keyboard=[
  [
    InlineKeyboardButton(text="Start Chat💬", callback_data="$chat_with_user"),
    InlineKeyboardButton(text="Admins ⭐️", callback_data="$all_admins"),
  ],
  [
    InlineKeyboardButton(text="Post to Channels 🗞", callback_data="$channels"),
    InlineKeyboardButton(text="Advertisement 🗞", callback_data="$ad_all")
  ],
  [
    InlineKeyboardButton(text="Data of Users 💾", callback_data="$show_download")
  ],
  [
    InlineKeyboardButton(text="Delete User🗑", callback_data="$delete_user")
  ],
])

data_base = InlineKeyboardMarkup(inline_keyboard=[
  [
    InlineKeyboardButton(text="Download data ⬇️", callback_data="$download_data")
  ],
  [
    InlineKeyboardButton(text="Show all users 🖨", callback_data="$show_users")
  ],
  [
    InlineKeyboardButton(text="Statistics 📊", callback_data="$statistic")
  ],
  [
    InlineKeyboardButton(text="🔙 Back", callback_data="$back_at_admin")
  ]
])

cancel_ad = InlineKeyboardMarkup(inline_keyboard=[
  [
    InlineKeyboardButton(text="Cancel ❌", callback_data="$cancel_ad")
  ]
])

delete_user = InlineKeyboardMarkup(inline_keyboard=[
  [
    InlineKeyboardButton(text="No ❌", callback_data="$cancel_ad")
  ],
  [
    InlineKeyboardButton(text="Yes ✅", callback_data="$delete")
  ],
])

send_finsh_kb = InlineKeyboardMarkup(inline_keyboard=[
  [
    InlineKeyboardButton(text="Cancel ❌", callback_data="$cancel_ad")
  ],
  
  [
    InlineKeyboardButton(text="Send Message📤", callback_data="$send_to_the_user")
  ]
])

back_admin = InlineKeyboardMarkup(inline_keyboard=[
  [
    InlineKeyboardButton(text="🔙 Back", callback_data="$back_at_admin")
  ]
])

admin_user = InlineKeyboardMarkup(inline_keyboard=[
  [
    InlineKeyboardButton(text="Admin ⭐️", callback_data="$admin")
  ],
  
  [
    InlineKeyboardButton(text="Normal User 👤", callback_data="$normal_user")
  ]
])

send_ad = InlineKeyboardMarkup(inline_keyboard=[
  [
    InlineKeyboardButton(text="Cancel ❌", callback_data="$cancel_ad")
  ],
  
  [
    InlineKeyboardButton(text="Send Message📤", callback_data="$sendad")
  ]
])

admins_add_kb = InlineKeyboardMarkup(inline_keyboard=[
  [
    InlineKeyboardButton(text="➕", callback_data="$add_admin"),
    InlineKeyboardButton(text="➖", callback_data="$remuve_admins"),
  ],
  [
    InlineKeyboardButton(text="🔙 Back", callback_data="$back_admin_panel")
  ]
])

done_admin = InlineKeyboardMarkup(inline_keyboard=[
  [
    InlineKeyboardButton(text="ADD ✅", callback_data="$add_the_admin"),
    InlineKeyboardButton(text="Cancle ❌", callback_data="$cancel_ad_list"),
  ]
])

done_remove = InlineKeyboardMarkup(inline_keyboard=[
  [
    InlineKeyboardButton(text="Remuve ✅", callback_data="$remove_admin"),
    InlineKeyboardButton(text="Cancle ❌", callback_data="$cancel_ad_list"),
  ]
])

back_data = InlineKeyboardMarkup(inline_keyboard=[
  [
    InlineKeyboardButton(text="🔙 Back", callback_data="$back_show")
  ]
])