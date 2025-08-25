import asyncio

from data.loader import bot

from database.DB_CONN_async import Session_db
from database.models_sql_async import Keys
from database.functions_db_async import get_data_for_delet_client, delete_user_db_on_server, delete_user_sub_db

from logs.admin_notify import notify_admin
from logs.logging_config import logger

from api_3xui.client import delete_client
from api_3xui.authorize import login_with_credentials

from sqlalchemy import select
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from contextlib import suppress


# ==================== НАСТРОЙКИ ИНТЕРВАЛОВ УВЕДОМЛЕНИЙ ====================
TEST_MODE = False
if TEST_MODE:
    NOTIFY_BEFORE_2_DAYS = timedelta(seconds=50)  # → Через 30 сек
    NOTIFY_BEFORE_1_DAY = timedelta(seconds=39)  # → Через 25 сек
    NOTIFY_BEFORE_12_HOURS = timedelta(seconds=28)  # → Через 20 сек
    NOTIFY_BEFORE_1_HOUR = timedelta(seconds=17)  # → Через 15 сек

    NOTIFY_AFTER_1_DAY = timedelta(seconds=20)  # → Через 30 сек после истечения
    NOTIFY_AFTER_2_DAYS = timedelta(seconds=33)  # → Через 40 сек после истечения

    DELETE_AFTER = timedelta(seconds=47)  # → Удалить через 45 сек после истечения

    # Интервал проверки должен быть МЕНЬШЕ самого маленького интервала уведомлений!
    CHECK_INTERVAL = timedelta(seconds=10)  # Интервал запуска проверки пользователей для отправки уведомлений

else:
    NOTIFY_BEFORE_2_DAYS = timedelta(days=2)
    NOTIFY_BEFORE_1_DAY = timedelta(days=1)
    NOTIFY_BEFORE_12_HOURS = timedelta(hours=12)
    NOTIFY_BEFORE_1_HOUR = timedelta(hours=1)

    NOTIFY_AFTER_1_DAY = timedelta(days=1)
    NOTIFY_AFTER_2_DAYS = timedelta(days=2)

    DELETE_AFTER = timedelta(days=3)
    CHECK_INTERVAL = timedelta(minutes=15)  # Интервал запуска проверки пользователей для отправки уведомлений

# ==================== НАСТРОЙКИ ТЕКСТОВ УВЕДОМЛЕНИЙ ====================

MESSAGE_2_DAYS = "🔔 Ваша подписка заканчивается через 2 дня.\n❗️ Чтобы не потерять доступ, продлите её заранее."
MESSAGE_1_DAY = "🔔 Ваша подписка заканчивается через 1 день.\n❗️ Чтобы не потерять доступ, продлите её заранее."
MESSAGE_12_HOURS = "🔔 Ваша подписка заканчивается через 12 часов.\n❗️ Чтобы не потерять доступ, продлите её заранее."
MESSAGE_1_HOUR = "🔔 Ваша подписка заканчивается через 1 час.\n❗️ Чтобы не потерять доступ, продлите её заранее."

MESSAGE_EXPIRED = "⚠️ Ваша подписка истекла.\n❗️ Продлите её, чтобы восстановить доступ к сервису."
MESSAGE_REMINDER_DAY1 = "🔔 Напоминание: Ваша подписка истекла 1 день назад.\n❗️ Продлите её, чтобы восстановить доступ, иначе через 2 дня она будет удалена."
MESSAGE_REMINDER_DAY2 = "🔔 Напоминание: Ваша подписка истекла 2 дня назад.\n❗️ Продлите её, чтобы восстановить доступ, иначе завтра она будет удалена."

MESSAGE_DELETED = "🛑 Ваша подписка была удалена, так как она истекла 3 дня назад."


# ==================== КНОПКА ДЛЯ ПРОДЛЕНИЯ ====================

renew_button = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Продлить подписку", callback_data="pay_subscribe")]
    ]
)

# ==================== ФУНКЦИИ ====================

async def send_message_to_user(telegram_id: int, message: str):
    try:
        await bot.send_message(telegram_id, message, reply_markup=renew_button)
        logger.info(f"[Уведомления подписок] Уведомление отправлено пользователю {telegram_id}")
    except Exception as e:
        logger.error(f"[Уведомления подписок] Не удалось отправить сообщение пользователю {telegram_id}: {e}")
        await notify_admin(f"[Уведомления подписок] Не удалось отправить сообщение пользователю {telegram_id}: {e}")


async def delete_user_data(telegram_id: int, server_id: str, client_uuid: str, ip_limit: int):
    """Безопасное удаление пользовательских данных"""
    session_3x_ui = None
    try:
        session_3x_ui = await login_with_credentials(server_name=server_id)
        if not session_3x_ui:
            error_msg = f'[Уведомления подписок] Не удалось авторизоваться на сервере {server_id} для удаления пользователя {telegram_id}'
            logger.error(error_msg)
            await notify_admin(error_msg)
            return False

        deletion_result = await delete_client(session_3x_ui, server_id, client_uuid)

        if deletion_result:
            await delete_user_db_on_server(
                quantity_users=ip_limit,
                server_name=server_id,
                telegram_id=telegram_id
            )
            await delete_user_sub_db(telegram_id)

            await send_message_to_user(telegram_id, MESSAGE_DELETED)
            logger.info(f"Пользователь {telegram_id} успешно удален после истечения подписки")
            return True
        else:
            error_msg = f"[Уведомления подписок] Удаление клиента на сервере {server_id} не удалось для пользователя {telegram_id}"
            logger.error(error_msg)
            await notify_admin(error_msg)
            return False

    except Exception as e:
        error_msg = f"[Уведомления подписок] Ошибка удаления пользователя {telegram_id}: {e}"
        logger.error(error_msg)
        await notify_admin(error_msg)
        return False
    finally:
        if session_3x_ui:
            with suppress(Exception):
                await session_3x_ui.close()


async def check_and_notify_expired_subscriptions():
    """Основная функция проверки и уведомлений"""
    start_time = datetime.now()
    processed_users = 0
    notifications_sent = 0
    errors_count = 0

    try:
        logger.info("[Уведомления] 🔄 Запуск проверки подписок...")
        async with (Session_db() as session):
            now = datetime.now()

            result = await session.execute(
                select(Keys).where(Keys.deleted_at.is_not(None))
            )
            users = result.scalars().all()
            processed_users = len(users)

            for user in users:
                try:
                    if not user.deleted_at:
                        continue

                    telegram_id = user.telegram_id
                    time_remaining = user.deleted_at - now
                    last_notification = user.last_notification_sent

                    # Уведомления до истечения подписки
                    notify_intervals =[
                        (NOTIFY_BEFORE_2_DAYS, MESSAGE_2_DAYS),
                        (NOTIFY_BEFORE_1_DAY, MESSAGE_1_DAY),
                        (NOTIFY_BEFORE_12_HOURS, MESSAGE_12_HOURS),
                        (NOTIFY_BEFORE_1_HOUR, MESSAGE_1_HOUR)
                    ]

                    notification_sent = False

                    for interval, message_text in notify_intervals:
                        if timedelta(seconds=0) < time_remaining <= interval:
                            if not last_notification or last_notification < user.deleted_at - interval:
                                await send_message_to_user(telegram_id, message_text)
                                user.last_notification_sent = now
                                await session.commit()
                                notification_sent = True
                                notifications_sent += 1

                                break

                    # Уведомление об истечении подписки
                    if time_remaining <= timedelta(seconds=0):
                        if (not last_notification or last_notification < user.deleted_at) and not notification_sent:
                            await send_message_to_user(telegram_id, MESSAGE_EXPIRED)
                            user.last_notification_sent = now
                            await session.commit()
                            notifications_sent += 1

                    # Напоминания после истечения
                    if time_remaining <= timedelta(seconds=0):
                        time_since_expired = now - user.deleted_at

                        reminder_intervals = [
                            (NOTIFY_AFTER_1_DAY, MESSAGE_REMINDER_DAY1),
                            (NOTIFY_AFTER_2_DAYS, MESSAGE_REMINDER_DAY2)
                        ]

                        for interval, message_text in reminder_intervals:
                            if time_since_expired >= interval:
                                if not last_notification or last_notification < user.deleted_at + interval:
                                    await send_message_to_user(telegram_id, message_text)
                                    user.last_notification_sent = now
                                    await session.commit()
                                    notifications_sent += 1

                                    break

                    # Удаление пользователя через указанное время после истечения
                    if user.deleted_at <= now:
                        time_since_expired = now - user.deleted_at
                        if time_since_expired >= DELETE_AFTER:
                            data_for_delete = await get_data_for_delet_client(telegram_id)

                            if data_for_delete:
                                server_id, client_uuid, ip_limit = data_for_delete
                                await delete_user_data(telegram_id, server_id, client_uuid, ip_limit)
                            else:
                                error_msg = f"Данные для удаления не найдены для пользователя {telegram_id}"
                                logger.error(error_msg)
                                await notify_admin(error_msg)

                except Exception as e:
                    errors_count += 1
                    logger.error(f"Ошибка обработки пользователя {user.telegram_id if user else 'Unknown'}: {e}")
                    continue

        duration = (datetime.now() - start_time).total_seconds()

        if notifications_sent > 0:
            logger.info(f"[Уведомления] ✅ Проверка завершена:")
            logger.info(f"⏱ Время: {duration:.2f} сек")
            logger.info(f"👥 Обработано пользователей: {processed_users}")
            logger.info(f"📨 Отправлено уведомлений: {notifications_sent}")
            logger.info(f"❌ Ошибок: {errors_count}")
        else:
            logger.info(f"[Уведомления] ✅ Проверка завершена. Уведомлений нет. "
                        f"Время: {duration:.2f} сек, Пользователей: {processed_users}")

    except Exception as e:
        error_message = f"❌ Критическая ошибка в уведомлениях подписок: {str(e)[:200]}"
        logger.error(f"[Уведомления] 🚨 {error_message}")
        await notify_admin(error_message)


async def start_subscription_checker():
    try:
        scheduler = AsyncIOScheduler()
        # Проверяем с указанным интервалом
        scheduler.add_job(
            check_and_notify_expired_subscriptions,
            trigger='interval',
            minutes=CHECK_INTERVAL.total_seconds() / 60
        )
        scheduler.start()

        logger.info(f"Запущен планировщик проверки подписок (интервал: {CHECK_INTERVAL})")

    except Exception as e:
        error_text = f"❗️ Внимание! Планировщик подписок упал с ошибкой:\n{e}"
        logger.error(error_text)
        await notify_admin(text=error_text)


async def init_subscription_notifier():
    """Инициализация уведомлений для запуска из main.py"""
    try:
        # Запускаем первую проверку сразу при старте
        await check_and_notify_expired_subscriptions()
        logger.info("✅ Первоначальная проверка подписок выполнена")
    except Exception as e:
        logger.error(f"Ошибка при первоначальной проверке подписок: {e}")
        await notify_admin(f"❌ Ошибка при первоначальной проверке подписок: {e}")

if __name__ == "__main__":
    asyncio.run(start_subscription_checker())

