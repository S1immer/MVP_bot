from aiogram import Bot, Dispatcher
from data.config import config_file

bot = Bot(config_file['token'])
dp = Dispatcher(bot=bot)
