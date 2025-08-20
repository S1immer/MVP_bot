from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from data.config import token  # Импортируем токен из config.py

storage = MemoryStorage()
bot = Bot(token)
dp = Dispatcher(bot=bot, storage=storage)


