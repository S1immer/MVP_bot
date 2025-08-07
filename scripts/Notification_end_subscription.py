import asyncio

from data.loader import bot

from database.DB_CONN_async import Session_db
from database.models_sql_async import Keys
from database.functions_db_async import get_data_for_delet_client, delete_user_db_on_server, delete_user_sub_db

from logs.admin_notify import notify_admin
from logs.logging_config import logger

from api_3xui.client import  delete_client
from api_3xui.authorize import login_with_credentials

from sqlalchemy import select

from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler



# Функция отправки уведомлений
async def send_message_to_user(telegram_id: int, message: str):
    # Пример, нужно заменить на свой метод отправки сообщений в Telegram
    await bot.send_message(telegram_id, message)

# Основная логика для проверки подписок
async def check_and_notify_expired_subscriptions():
    async with Session_db() as session:
        now = datetime.now()

        # Получаем всех пользователей с их подписками
        result = await session.execute(select(Keys))
        users = result.scalars().all()

        for user in users:
            telegram_id = user.telegram_id


            if user.deleted_at:
                expired_at = user.deleted_at
                time_remaining = expired_at - now
                last_notification_sent = user.last_notification_sent


                notify_1day = 1 # день
                notify_12hours = 12 # часов
                notify_1hour = 1 # час

                # Если прошло больше 70% времени с последнего уведомления, сбрасываем его
                if last_notification_sent and (now - last_notification_sent) > (
                        0.7 * (expired_at - last_notification_sent)):
                    user.last_notification_sent = None
                    await session.commit()

                # Отправляем уведомления за 1 день, 12 часов, 1 час
                if timedelta(days=0) < time_remaining <= timedelta(days=notify_1day) and (
                        not last_notification_sent or last_notification_sent < now - timedelta(days=1)):
                    await send_message_to_user(user.telegram_id,
                                               message="Ваша подписка истекает через 1 день. Пожалуйста, продлите.")
                    user.last_notification_sent = now
                    await session.commit()

                elif timedelta(hours=0) < time_remaining <= timedelta(hours=notify_12hours) and (
                        not last_notification_sent or last_notification_sent < now - timedelta(hours=12)):
                    await send_message_to_user(user.telegram_id,
                                               message="Ваша подписка истекает через 12 часов. Пожалуйста, продлите.")
                    user.last_notification_sent = now
                    await session.commit()

                elif timedelta(minutes=0) < time_remaining <= timedelta(hours=notify_1hour) and (
                        not last_notification_sent or last_notification_sent < now - timedelta(hours=1)):
                    await send_message_to_user(user.telegram_id,
                                               message="Ваша подписка истекает через 1 час. Пожалуйста, продлите.")
                    user.last_notification_sent = now
                    await session.commit()


                # Если подписка истекла 3 дня назад - удаляем пользователя
                if expired_at < now - timedelta(days=3):

                    data_for_delete = await get_data_for_delet_client(telegram_id)

                    if data_for_delete:
                        server_id, client_uuid, ip_limit = data_for_delete
                        try:
                            session_3x_ui = await login_with_credentials(server_name=server_id)
                            deletion_result = await delete_client(session_3x_ui, server_id, client_uuid)
                            if deletion_result:
                                await delete_user_db_on_server(quantity_users=ip_limit,
                                                               server_name=server_id,
                                                               telegram_id=telegram_id)
                                await delet_user_sub_db(telegram_id)

                                await session_3x_ui.close()
                                await send_message_to_user(telegram_id,
                                                    message="Ваша подписка была удалена, так как она истекла 3 дня назад.")
                            else:
                                logger.error(
                                    f"[автопроверка подписок] Удаление клиента на сервере не удалось для пользователя {telegram_id}.")
                                await notify_admin(
                                    f"[автопроверка подписок] Не удалось удалить клиента на сервере [{server_id}] для пользователя {telegram_id}.")
                        except Exception as e:
                            logger.error(f"[автопроверка подписок] У пользователя {telegram_id} возникла с удалением профиля ошибка: {e}")
                    else:
                        logger.error(f"Данные для удаления не найдены для пользователя {telegram_id}.")
                        await notify_admin(f"Данные для удаления не найдены для пользователя {telegram_id}.")


# Функция для планирования задач
async def start_subscription_checker():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_and_notify_expired_subscriptions, trigger='interval', seconds=5)
    scheduler.start()

    while True:
        await asyncio.sleep(1)

# Запуск
if __name__ == "__main__":
    asyncio.run(start_subscription_checker())

