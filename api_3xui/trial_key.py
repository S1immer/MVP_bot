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


        if response and response.get("success"):
            connect_link = await link(session, server_id_name, client_uuid, str(telegram_id))

            return connect_link, client_uuid, limit_ip, server_id_name, expiry_time

        else:
            await notify_admin(f"Ошибка создания тестового ключа для {telegram_id} - response.get not success")
            logger.error(f"Ошибка создания тестового ключа для {telegram_id} - response.get not success")
            return None
    except Exception as e:
        logger.error(f"Ошибка создания тестового ключа для {telegram_id}: {e}")
        return None
    finally:
        # Закрываем сессию, если она есть и не закрыта
        if session:
            await session.close()