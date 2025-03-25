import asyncio
import logging
from data.louder import dp, bot
from handlers import user_menu, admin_menu
from keyboard import user_keyboard

logging.basicConfig(filename='log.txt')


async def main():
    await user_menu.set_commands()
    dp.include_router(user_menu.router)
    dp.include_router(admin_menu.router)
    dp.include_router(user_keyboard.router)
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
