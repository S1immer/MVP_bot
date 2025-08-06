# import asyncio
from api_3xui.authorize import login_with_credentials

from database.functions_db_async import get_least_loaded_server

from datetime import datetime, timedelta

from api_3xui.client import add_user
from api_3xui.authorize import link

from logs.logging_config import logger
from logs.admin_notify import notify_admin

from data_servers.tariffs import tariffs_data
from uuid import uuid4



async def create_trial_key(telegram_id: int):

    session = None

    try:
        server_id_name = await get_least_loaded_server()
        session = await login_with_credentials(server_id_name)

        period = 'trial'
        devices = '1_devices'
        tariff_data = tariffs_data[period][devices]
        tariff_days = tariff_data['days']
        limit_ip = tariff_data['device_limit']

        current_time = datetime.now()
        expiry_time = current_time + timedelta(days=tariff_days)
        expiry_timestamp = int(expiry_time.timestamp() * 1000)

        client_uuid = str(uuid4())

        response = await add_user(session, server_id_name, client_uuid, str(telegram_id),
                                  limit_ip=limit_ip+1, total_gb=0, expiry_time=expiry_timestamp, # +1 чтобы на сервере при смене интернета не заблокировался ключ
                                  enable=True, flow="xtls-rprx-vision")


        if response.get("success"):
            connect_link = await link(session, server_id_name, client_uuid, str(telegram_id))
            print(connect_link)

            # await save_key_to_database(telegram_id=telegram_id, client_uuid=client_uuid,
            #                            active_key=connect_link, ip_limit=limit_ip, server_id=server_id_name, expiry_time=expiry_time)

            return connect_link, client_uuid, limit_ip, server_id_name, expiry_time

        else:
            await notify_admin(f"Ошибка создания тестового ключа для {telegram_id}")
            logger.warning(f"Ошибка создания тестового ключа для {telegram_id}")
            return None
    except Exception as e:
        logger.error(f"Ошибка создания тестового ключа для {telegram_id}: {e}")
        return None
    finally:
        # Закрываем сессию, если она есть и не закрыта
        if session:
            await session.close()


# if __name__ == "__main__":
#     test_telegram_id = 123456789 # <-- Замените на ваш Telegram ID
#     client_uuid = str(uuid4())
#
#     async def main():
#         result = await create_trial_key(test_telegram_id, client_uuid)
#         if result:
#             print("Ключ успешно создан!")
#         else:
#             print("Не удалось создать ключ.")
#
#     asyncio.run(main())




# async def create_trial_key(tg_id: int):
#     conn = await asyncpg.connect(DATABASE_URL)
#     try:
#         server_id = await get_least_loaded_server(conn)
#         session = await login_with_credentials(server_id, ADMIN_USERNAME, ADMIN_PASSWORD)
#         current_time = datetime.utcnow()
#
#         expiry_time = current_time + timedelta(days=1, hours=3)
#         expiry_timestamp = int(expiry_time.timestamp() * 1000)
#
#         client_id = str(uuid.uuid4())
#         email = generate_random_email()
#         response = await add_client(
#             session, server_id, client_id, email, tg_id,
#             limit_ip=1, total_gb=0, expiry_time=expiry_timestamp,
#             enable=True, flow="xtls-rprx-vision"
#         )
#
#         if response.get("success"):
#             # Генерация ссылки подписки
#             connection_link = await link_subscription(email, server_id)
#
#             existing_connection = await conn.fetchrow('SELECT * FROM connections WHERE tg_id = $1', tg_id)
#
#             if existing_connection:
#                 await conn.execute('UPDATE connections SET trial = 1 WHERE tg_id = $1', tg_id)
#             else:
#                 await add_connection(tg_id, 0, 1)
#
#             await store_key(tg_id, client_id, email, expiry_timestamp, connection_link, server_id)
#
#             instructions = INSTRUCTIONS
#             return {
#                 'key': connection_link,
#                 'instructions': instructions
#             }
#         else:
#             return {'error': 'Не удалось добавить клиента на панель'}
#     finally:
#         await conn.close()