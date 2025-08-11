# import asyncio
from uuid import uuid4

from database.functions_db_async import get_least_loaded_server

from api_3xui.authorize import login_with_credentials, get_clients, link
from api_3xui.client import add_user

from data_servers.tariffs import tariffs_data

from datetime import datetime, timedelta

from logs.admin_notify import notify_admin
from logs.time_logging import time_logg
from logs.logging_config import logger



async def key_generation(telegram_id: int, period: str, devices: str):
    """"
    :param telegram_id - telegram_id пользователя
    :param period - пример 'month', 'three_months'
    :param devices - ip_limit для пользователя
    """
    session = None
    server_id_name = None

    try:
        server_id_name = await get_least_loaded_server()
        print(f"Выбран сервер - {server_id_name}")
        print("Создаю сессию")
        session = await login_with_credentials(server_id_name)
        print("Сессия создана")
        print("Авторизация успешна")

        # Далее ваша логика добавления пользователя и получения ключа
        client_uuid = str(uuid4())

        tariff_data = tariffs_data[period][f"{devices}_devices"]
        tariff_days = tariff_data['days']
        device = tariff_data['device_limit']

        current_time = datetime.now()
        expiry_time = current_time + timedelta(days=tariff_days)
        expiry_timestamp = int(expiry_time.timestamp() * 1000)

        await add_user(
            session,
            server_id_name,
            client_uuid,
            str(telegram_id),
            device + 1,
            total_gb=0,
            expiry_time=expiry_timestamp,
            enable=True,
            flow='xtls-rprx-vision'
        )

        response = await get_clients(session, server_id_name)

        if 'obj' not in response or len(response['obj']) == 0:
            return None

        link_data = await link(
            session,
            server_id_name,
            client_uuid,
            str(telegram_id)
        )

        return link_data, server_id_name, tariff_days, device, client_uuid

    except Exception as e:
        logger.error(f"[key_generation] у пользователя {telegram_id} произошла ошибка с созданием ключа: {e}")
        await notify_admin(text=f"У пользователя {telegram_id} произошла ошибка с созданием ключа!\n"
                                f"Сервер: {server_id_name} "
                                f"Ошибка: {e}\n"
                                f"Функция: key_generation\n"
                                f"Время: {time_logg}")
        return None

    finally:
        print("Закрываю сессию")
        if session:
            await session.close()
            print("Сессия закрыта")


# # Тестирование функции
# async def main():
#     telegram_id = 99999235
#     period = 'month'
#     devices = '1_devices'
#     # period = 'sagdser'
#     # devices = 'gsdehs'
#
#     key = await key_generation(telegram_id, period, devices)
#     if key:
#         print(f"Тестовый ключ: {key}")
#     else:
#         print("Не удалось получить тестовый ключ.")
#
#
# if __name__ == "__main__":
#     asyncio.run(main())
