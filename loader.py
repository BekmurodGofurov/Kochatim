from aiogram import Bot, Dispatcher, types
import asyncio
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.contrib.fsm_storage.memory import MemoryStorage

from data import config
# PROXY_URL = "http://proxy.server:3128"

bot = Bot(token=config.BOT_TOKEN, parse_mode=types.ParseMode.HTML )#proxy=PROXY_URL
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())
