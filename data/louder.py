from aiogram import Bot, types, Dispatcher, Router, F
from data.config import config_file

bot = Bot(config_file['token'])
dp = Dispatcher(bot=bot)
