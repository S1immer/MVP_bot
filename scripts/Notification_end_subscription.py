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


# ==================== НАСТРОЙКИ ИНТЕРВАЛОВ УВЕДОМЛЕНИЙ ====================

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

    except Exception as e:
        logger.error(f"Не удалось отправить сообщение пользователю {telegram_id}: {e}")
        await notify_admin(f"[Уведомления подписок] Не удалось отправить сообщение пользователю {telegram_id}: {e}")


async def check_and_notify_expired_subscriptions():
    async with Session_db() as session:
        now = datetime.now()

        result = await session.execute(
            select(Keys).where(Keys.deleted_at.is_not(None))
        )
        users = result.scalars().all()

        for user in users:
            if not user.deleted_at:
                continue

            telegram_id = user.telegram_id
            time_remaining = user.deleted_at - now
            last_notification = user.last_notification_sent

            # Уведомления до истечения подписки
            notify_intervals = [
                (NOTIFY_BEFORE_2_DAYS, MESSAGE_2_DAYS),
                (NOTIFY_BEFORE_1_DAY, MESSAGE_1_DAY),
                (NOTIFY_BEFORE_12_HOURS, MESSAGE_12_HOURS),
                (NOTIFY_BEFORE_1_HOUR, MESSAGE_1_HOUR)
            ]

            notification_sent = False

            for interval, message_text in notify_intervals:
                if timedelta(seconds=0) < time_remaining <= interval:
                    # Отправляем уведомление только если еще не отправляли для этого интервала
                    if not last_notification or last_notification < user.deleted_at - interval:
                        try:
                            await send_message_to_user(telegram_id, message_text)
                            user.last_notification_sent = now
                            await session.commit()
                            notification_sent = True
                            break
                        except Exception as e:
                            logger.error(f"[Уведомления подписок] Ошибка отправки уведомления пользователю {telegram_id}: {e}")

            # Уведомление об истечении подписки (первое уведомление)
            if time_remaining <= timedelta(seconds=0):
                # Отправляем только если еще не отправляли уведомление об истечении
                if (not last_notification or last_notification < user.deleted_at) and not notification_sent:
                    try:
                        await send_message_to_user(telegram_id, MESSAGE_EXPIRED)
                        user.last_notification_sent = now
                        await session.commit()
                    except Exception as e:
                        logger.error(f"[Уведомления подписок] Ошибка отправки уведомления об истечении пользователю {telegram_id}: {e}")

            # Ежедневные напоминания после истечения
            if time_remaining <= timedelta(seconds=0):
                time_since_expired = now - user.deleted_at

                # Напоминания после истечения (только 1 и 2 дня)
                reminder_intervals = [
                    (NOTIFY_AFTER_1_DAY, MESSAGE_REMINDER_DAY1),
                    (NOTIFY_AFTER_2_DAYS, MESSAGE_REMINDER_DAY2)
                ]

                for interval, message_text in reminder_intervals:
                    if time_since_expired >= interval:
                        # Отправляем уведомление только если еще не отправляли для этого интервала
                        if not last_notification or last_notification < user.deleted_at + interval:
                            try:
                                await send_message_to_user(telegram_id, message_text)
                                user.last_notification_sent = now
                                await session.commit()
                                logger.info(f"[Уведомления подписок] Отправлено напоминание через {interval} пользователю {telegram_id}")
                                break  # Прерываем после отправки одного уведомления
                            except Exception as e:
                                logger.error(f"[Уведомления подписок] Ошибка отправки напоминания пользователю {telegram_id}: {e}")

            # Удаление пользователя через указанное время после истечения
            if user.deleted_at <= now:  # Подписка уже истекла
                time_since_expired = now - user.deleted_at
                if time_since_expired >= DELETE_AFTER:  # Истекла более N времени назад
                    data_for_delete = await get_data_for_delet_client(telegram_id)

                    if data_for_delete:
                        server_id, client_uuid, ip_limit = data_for_delete
                        session_3x_ui = None
                        try:
                            session_3x_ui = await login_with_credentials(server_name=server_id)
                            if not session_3x_ui:
                                logger.error(text=f'[Уведомления подписок] Для удаления пользователя - {telegram_id} с сервера '
                                                        f'[{server_id}] не удалось авторизоваться!')
                                await notify_admin(text=f'[Уведомления подписок] Для удаления пользователя - {telegram_id} с сервера '
                                                        f'[{server_id}] не удалось авторизоваться!')
                                return
                            deletion_result = await delete_client(session_3x_ui, server_id, client_uuid)

                            if deletion_result:
                                await delete_user_db_on_server(
                                    quantity_users=ip_limit,
                                    server_name=server_id,
                                    telegram_id=telegram_id
                                )
                                await delete_user_sub_db(telegram_id)

                                await send_message_to_user(telegram_id, MESSAGE_DELETED)
                                logger.info(f"[Уведомления подписок] Пользователь {telegram_id} удален после истечения подписки")

                            else:
                                logger.error(f"[Уведомления подписок] Удаление клиента на сервере {server_id} не удалось для пользователя {telegram_id}")
                                await notify_admin(
                                    f"[Уведомления подписок] Не удалось удалить клиента на сервере [{server_id}] "
                                    f"для пользователя {telegram_id}."
                                )
                        except Exception as e:
                            logger.error(f"Ошибка удаления пользователя {telegram_id}: {e}")
                            await notify_admin(f"Ошибка при удаления пользователя {telegram_id}, ошибка: {e}")
                        finally:
                            if session_3x_ui:
                                await session_3x_ui.close()
                    else:
                        logger.error(f"Данные для удаления не найдены для пользователя {telegram_id}")
                        await notify_admin(
                            f"Сработало уведомление на удаление пользователя - {telegram_id}, "
                            f"но не все данные были найдены для удаления.\n"
                            f"Проверить удален ли пользователь с сервера и базы данных!"
                        )


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

        while True:
            await asyncio.sleep(1)

    except Exception as e:
        error_text = f"❗️ Внимание! Планировщик подписок упал с ошибкой:\n{e}"
        logger.error(error_text)

        try:
            await notify_admin(text=error_text)
        except Exception as notify_exc:
            logger.error(f"Не удалось отправить уведомление админу: {notify_exc}")


if __name__ == "__main__":
    asyncio.run(start_subscription_checker())

