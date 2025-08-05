import asyncio
from data.loader import dp, bot
from handlers import user_menu, admin_menu
from keyboard import user_keyboard
from database.DB_CONN_async import engine, DeclBase
from logs.admin_notify import notify_admin
from logs.time_logging import time_logg
from logs.logging_config import logger



async def create_missing_tables():
    async with engine.begin() as conn:
        await conn.run_sync(DeclBase.metadata.create_all)



async def main():
    await create_missing_tables()

    await user_menu.set_commands()
    dp.include_router(user_menu.router)
    dp.include_router(admin_menu.router)
    dp.include_router(user_keyboard.router)



    try:
        logger.info("Бот успешно запущен!")
        await notify_admin(text=f"✅ Бот успешно запущен!\n"
                           f"⏳ Время запуска: {time_logg} (локальное сервера).")
        await dp.start_polling(bot)

    except KeyboardInterrupt as e:
        logger.error(f"Завершение работы бота с ошибкой: {e}")
        await notify_admin(text=f"⛔️ Бот завершил работу с ошибкой: {e}\n"
                                f"⏳ Время завершения: {time_logg} (локальное сервера)")

    except Exception as e:
        logger.error(f"Завершение работы бота с ошибкой: {e}")
        await notify_admin(text=f"❌ Завершение работы бота c ошибкой!\n"
                                f"Ошибка: {e}"
                                f"⏳ Время завершения: {time_logg} (локальное сервера)")


    finally:
        logger.warning("Завершение работы бота!")
        await notify_admin(text=f"❌ Завершение работы бота!\n"
                                f"⏳ Время завершения: {time_logg} (локальное сервера)")
        await bot.session.close()


if __name__ == '__main__':
    asyncio.run(main())
