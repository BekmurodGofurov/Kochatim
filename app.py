from aiogram import executor
from data import database as db
from loader import dp
import middlewares, filters, handlers
from utils.notify_admins import on_startup_notify
from utils.set_bot_commands import set_default_commands


async def on_startup(dispatcher):
  await set_default_commands(dispatcher)
  await db.db_start()
  print("Created sqlite")
  await on_startup_notify(dispatcher)


if __name__ == '__main__':
  executor.start_polling(dp, on_startup=on_startup, skip_updates=True)
