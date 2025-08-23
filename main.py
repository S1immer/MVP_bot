import asyncio
from data.loader import dp, bot
from handlers import user_menu, admin_menu
from keyboard import user_keyboard
from database.DB_CONN_async import engine, DeclBase
from logs.admin_notify import notify_admin
from logs.time_logging import time_logg
from logs.logging_config import logger
from payment.yookassa.payment_lock import PaymentLockMiddleware
from handlers.admin_menu.main_admin_menu import admin_router


async def create_missing_tables():
    async with engine.begin() as conn:
        await conn.run_sync(DeclBase.metadata.create_all)



async def main():
    try:
        await create_missing_tables()
    except Exception as e:
        logger.error(f"Ошибка создания таблиц БД при старте: {e}")
        try:
            await notify_admin(text=f"❌ Ошибка создания таблиц БД при старте: {e}\n"
                                   f"⏳ Время: {time_logg} (локальное сервера)")
        except Exception as notify_exc:
            logger.error(f"Не удалось уведомить админа о ошибке БД: {notify_exc}")
        return

    await user_menu.set_commands()
    dp.include_router(user_menu.router)
    dp.include_router(user_keyboard.router)
    dp.message.middleware(PaymentLockMiddleware())
    dp.callback_query.middleware(PaymentLockMiddleware())
    dp.include_router(admin_router)

    try:
        logger.info("Бот успешно запущен!")
        try:
            await notify_admin(text=f"✅ Бот успешно запущен!\n"
                               f"⏳ Время запуска: {time_logg} (локальное сервера).")
        except Exception as notify_exc:
            logger.error(f"Не удалось отправить уведомление о запуске: {notify_exc}")
        await dp.start_polling(bot)

    except KeyboardInterrupt as e:
        logger.error(f"Завершение работы бота с ошибкой: {e}")
        try:
            await notify_admin(text=f"⛔️ Бот завершил работу с ошибкой: {e}\n"
                                    f"⏳ Время завершения: {time_logg} (локальное сервера)")
        except Exception as e:
            logger.error(f"Не удалось уведомить админа о завершении с ошибкой: {e}")

    except Exception as e:
        logger.error(f"Завершение работы бота с ошибкой: {e}")
        try:
            await notify_admin(text=f"❌ Завершение работы бота c ошибкой!\n"
                                    f"Ошибка: {e}"
                                    f"⏳ Время завершения: {time_logg} (локальное сервера)")
        except Exception as e:
            logger.error(f"Не удалось уведомить админа о непредвиденной ошибке: {e}")


    finally:
        logger.warning("Завершение работы бота!")
        try:
            await notify_admin(text=f"❌ Завершение работы бота!\n"
                                    f"⏳ Время завершения: {time_logg} (локальное сервера)")
        except Exception as e:
            logger.error(f"Не удалось уведомить админа о завершении работы: {e}")
        await bot.session.close()


if __name__ == '__main__':
    asyncio.run(main())
