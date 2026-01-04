from aiogram.dispatcher.filters.state import State, StatesGroup

# Video State
class video_caption_button_state(StatesGroup):
  caption_video1 = State()
  video_video1 = State()
  button_name_video1 = State()
  url_video1 = State()
  channel_video1 = State()
class video_caption_state(StatesGroup):
  caption_video2 = State()
  video_video2 = State()
  channel_video2 = State()
class video_button_state(StatesGroup):
  video_video3 = State()
  button_name_video3 = State()
  url_video3 = State()
  channel_video3 = State()
class video_state(StatesGroup):
  video_video4 = State()
  channel_video4 = State()

# Photo State
class photo_caption_button_state(StatesGroup):
  photo_photo1 = State()
  caption_photo1 = State()
  button_name_photo1 = State()
  url_photo1 = State()
  channel_photo1 = State()
class photo_caption_state(StatesGroup):
  photo_photo2 = State()
  caption_photo2 = State()
  channel_photo2 = State()
class photo_button_state(StatesGroup):
  photo_photo3 = State()
  button_name_photo3 = State()
  url_photo3 = State()
  channel_photo3 = State()
class photo_state(StatesGroup):
  photo_photo4 = State()
  channel_photo4 = State()

# Music State
class music_caption_button_state(StatesGroup):
  music_music1 = State() 
  caption_music1 = State()
  button_name_music1 = State()
  url_music1 = State()
  channel_music1 = State()
class music_caption_state(StatesGroup):
  caption_music2 = State()
  music_music2 = State()
  channel_music2 = State()
class music_button_state(StatesGroup):
  music_music3 = State()
  button_name_music3 = State()
  url_music3 = State()
  channel_music3 = State()
class music_state(StatesGroup):
  music_music4 = State()
  channel_music4 = State()

# Text State
class text_button_state(StatesGroup):
  caption = State()
  button_name = State()
  url = State()
  channel = State()
class text_state(StatesGroup):
  caption_text = State()
  channel_text = State()
