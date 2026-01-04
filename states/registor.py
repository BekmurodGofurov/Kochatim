from aiogram.dispatcher.filters.state import State, StatesGroup

class Auth(StatesGroup):
  name = State()
  age = State()
  job = State()
  number = State()
  # photo = State()

class delete_state(StatesGroup):
  user_id = State()

class chat(StatesGroup):
  text_for_me = State()

class admin_send_chatID(StatesGroup):
  who = State()
  admin_message = State()

class bot_chat(StatesGroup):
  bot_fedback = State()
