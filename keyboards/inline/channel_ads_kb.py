from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
  
# Types of post
type_post = InlineKeyboardMarkup(inline_keyboard=[
  [
    InlineKeyboardButton(text="Video", callback_data="$video"),
    InlineKeyboardButton(text="Photo", callback_data="$photo")
  ],
  [
    InlineKeyboardButton(text="Music", callback_data="$music"),
    InlineKeyboardButton(text="Only Text", callback_data="$only_text")
  ],
  [
    InlineKeyboardButton(text="Cancel", callback_data="$cancel_post")
  ]
])

# Vido types
type_vido01 = InlineKeyboardMarkup(inline_keyboard=[
  [
    InlineKeyboardButton(text="Caption", callback_data="$video_cation"),
    InlineKeyboardButton(text="Button", callback_data="$send_video_button")
  ],
  [
    InlineKeyboardButton(text="Start", callback_data="$send_video"),
  ],
  [
    InlineKeyboardButton(text="Cancel", callback_data="$cancel_post")
  ]
])
type_vido02 = InlineKeyboardMarkup(inline_keyboard=[
  [
    InlineKeyboardButton(text="Button", callback_data="$send_video_caption_button")
  ],
  [
    InlineKeyboardButton(text="Start", callback_data="$send_video_caption"),
  ],
  [
    InlineKeyboardButton(text="Cancel", callback_data="$cancel_post")
  ]
])

# Photo types
type_photo1 = InlineKeyboardMarkup(inline_keyboard=[
  [
    InlineKeyboardButton(text="Caption", callback_data="$photo_caption"),
    InlineKeyboardButton(text="Button", callback_data="$send_photo_button")
  ],
  [
    InlineKeyboardButton(text="Start", callback_data="$send_photo"),
  ],
  [
    InlineKeyboardButton(text="Cancel", callback_data="$cancel_post")
  ]
])
type_photo02 = InlineKeyboardMarkup(inline_keyboard=[
  [
    InlineKeyboardButton(text="Button", callback_data="$send_photo_caption_button")
  ],
  [
    InlineKeyboardButton(text="Start", callback_data="$send_photo_caption"),
  ],
  [
    InlineKeyboardButton(text="Cancel", callback_data="$cancel_post")
  ]
])

# Music types
type_music01 = InlineKeyboardMarkup(inline_keyboard=[
  [
    InlineKeyboardButton(text="Caption", callback_data="$music_cation"),
    InlineKeyboardButton(text="Button", callback_data="$send_music_button")
  ],
  [
    InlineKeyboardButton(text="Start", callback_data="$send_music"),
  ],
  [
    InlineKeyboardButton(text="Cancel", callback_data="$cancel_post")
  ]
])
type_music02 = InlineKeyboardMarkup(inline_keyboard=[
  [
    InlineKeyboardButton(text="Button", callback_data="$send_music_caption_button")
  ],
  [
    InlineKeyboardButton(text="Start", callback_data="$send_music_caption"),
  ],
  [
    InlineKeyboardButton(text="Cancel", callback_data="$cancel_post")
  ]
])

# Text types
type_text= InlineKeyboardMarkup(inline_keyboard=[
  [
    InlineKeyboardButton(text="Button", callback_data="$send_text_button")
  ],
  [
    InlineKeyboardButton(text="Start", callback_data="$send_text"),
  ],
  [
    InlineKeyboardButton(text="Cancel", callback_data="$cancel_post")
  ]
])

# Sending Video post
send_video01 = InlineKeyboardMarkup(inline_keyboard=[
  [
    InlineKeyboardButton(text="Send post", callback_data="$postvideo01")
  ],
  [
    InlineKeyboardButton(text="Cancle", callback_data="$cancel_post")
  ]
])
send_video02 = InlineKeyboardMarkup(inline_keyboard=[
  [
    InlineKeyboardButton(text="Send post", callback_data="$postvideo02")
  ],
  [
    InlineKeyboardButton(text="Cancle", callback_data="$cancel_post")
  ]
])
send_video03 = InlineKeyboardMarkup(inline_keyboard=[
  [
    InlineKeyboardButton(text="Send post", callback_data="$postvideo03")
  ],
  [
    InlineKeyboardButton(text="Cancle", callback_data="$cancel_post")
  ]
])
send_video04 = InlineKeyboardMarkup(inline_keyboard=[
  [
    InlineKeyboardButton(text="Send post", callback_data="$postvideo04")
  ],
  [
    InlineKeyboardButton(text="Cancle", callback_data="$cancel_post")
  ]
])

# Sending Photo post
send_photo01 = InlineKeyboardMarkup(inline_keyboard=[
  [
    InlineKeyboardButton(text="Send post", callback_data="$postphoto01")
  ],
  [
    InlineKeyboardButton(text="Cancle", callback_data="$cancel_post")
  ]
])
send_photo02 = InlineKeyboardMarkup(inline_keyboard=[
  [
    InlineKeyboardButton(text="Send post", callback_data="$postphoto02")
  ],
  [
    InlineKeyboardButton(text="Cancle", callback_data="$cancel_post")
  ]
])
send_photo03 = InlineKeyboardMarkup(inline_keyboard=[
  [
    InlineKeyboardButton(text="Send post", callback_data="$postphoto03")
  ],
  [
    InlineKeyboardButton(text="Cancle", callback_data="$cancel_post")
  ]
])
send_photo04 = InlineKeyboardMarkup(inline_keyboard=[
  [
    InlineKeyboardButton(text="Send post", callback_data="$postphoto04")
  ],
  [
    InlineKeyboardButton(text="Cancle", callback_data="$cancel_post")
  ]
])

# Sending Music post
sent_music01 = InlineKeyboardMarkup(inline_keyboard=[
  [
    InlineKeyboardButton(text="Send post", callback_data="$postmusic01")
  ],
  [
    InlineKeyboardButton(text="Cancle", callback_data="$cancel_post")
  ]
])
sent_music02 = InlineKeyboardMarkup(inline_keyboard=[
  [
    InlineKeyboardButton(text="Send post", callback_data="$postmusic02")
  ],
  [
    InlineKeyboardButton(text="Cancle", callback_data="$cancel_post")
  ]
])
sent_music03 = InlineKeyboardMarkup(inline_keyboard=[
  [
    InlineKeyboardButton(text="Send post", callback_data="$postmusic03")
  ],
  [
    InlineKeyboardButton(text="Cancle", callback_data="$cancel_post")
  ]
])
sent_music04 = InlineKeyboardMarkup(inline_keyboard=[
  [
    InlineKeyboardButton(text="Send post", callback_data="$postmusic0")
  ],
  [
    InlineKeyboardButton(text="Cancle", callback_data="$cancel_post")
  ]
])

# Sending Text post
sent_text01 = InlineKeyboardMarkup(inline_keyboard=[
  [
    InlineKeyboardButton(text="Send post", callback_data="$posttext01")
  ],
  [
    InlineKeyboardButton(text="Cancle", callback_data="$cancel_post")
  ]
])
sent_text02 = InlineKeyboardMarkup(inline_keyboard=[
  [
    InlineKeyboardButton(text="Send post", callback_data="$posttext02")
  ],
  [
    InlineKeyboardButton(text="Cancle", callback_data="$cancel_post")
  ]
])

cancel_post_kb = InlineKeyboardMarkup(inline_keyboard=[
  [
    InlineKeyboardButton(text="Cancle", callback_data="$cancel_post")
  ]
])