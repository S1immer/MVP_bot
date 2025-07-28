from aiogram import Bot, Dispatcher
from data.config import token  # Импортируем токен из config.py

bot = Bot(token)
dp = Dispatcher(bot=bot)


