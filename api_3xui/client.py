import json
from data_servers.servers import SERVER_ID
from logs.logging_config import logger
from logs.admin_notify import notify_admin


async def add_user(session, server_id_name: str, client_uuid: str, telegram_id: str, limit_ip: int, total_gb: int, expiry_time: int, enable: bool, flow: str):
    """
    Добавляет пользователя в веб-панель 3X-UI.

    :param session: Сессия для запроса
    :param server_id_name: ID сервера
    :param client_uuid: Уникальный идентификатор пользователя
    :param telegram_id: ID Telegram
    :param limit_ip: Ограничение IP
    :param total_gb: Общий лимит трафика в ГБ
    :param expiry_time: Время истечения срока действия
    :param enable: Флаг активации
    :param flow: Тип потока
    """

    server = SERVER_ID[server_id_name]
    api_url = server['url']
    url = f'{api_url}/panel/api/inbounds/addClient'


    client_data = {
        "id": client_uuid,
        "email": telegram_id,
        "limitIp": limit_ip,
        "totalGB": total_gb,
        "expiryTime": expiry_time,
        "enable": enable,
        "flow": flow,
    }

    settings = json.dumps({"clients": [client_data]})

    data = {
        "id": 1,
        "settings": settings
    }

    headers = {
        'Content-Type': 'application/json',
    }

    async with session.post(url, json=data, headers=headers) as response:
        # print(f"Запрос на добавление пользователя: {data}")
        # print(f"Статус ответа: {response.status}")
        response_text = await response.text()
        # print(f"Ответ от сервера: {response_text}")

        if response.status == 200:
            # print(f"Пользователь добавлен: uuid={client_uuid}")
            return await response.json()
        else:
            logger.error(f"[add_user] Ошибка при добавлении пользователя {telegram_id}: {response.status}, {response_text}")
            await notify_admin(text=f"[add_user] Ошибка при добавлении пользователя {telegram_id} на сервер {server_id_name}!\n"
                                    f"Ошибка: {response.status}, {response_text}")
            return None


async def extend_client_key(session, server_id_name: str, client_uuid: str, limit_ip: int, telegram_id: int,
                            new_expiry_time: int) -> bool:
    """
    Расширяет подписку существующего клиента в веб-панели 3X-UI.

    :param session: aiohttp.ClientSession для HTTP-запросов
    :param server_id_name: Название сервера из словаря SERVER_ID
    :param client_uuid: Уникальный идентификатор клиента
    :param limit_ip: Лимит устройств (IP)
    :param telegram_id: Telegram ID клиента
    :param new_expiry_time: Новое время окончания подписки (UNIX timestamp)
    :return: True, если операция успешна, иначе False
    """
    telegram_id = str(telegram_id)
    server = SERVER_ID[server_id_name]
    api_url = server['url']

    updated_expiry_time = new_expiry_time

    payload = {
        "id": 1,
        "settings": json.dumps({
            "clients": [
                {
                    "id": client_uuid,
                    "email": telegram_id,
                    "limitIp": limit_ip,
                    "totalGB": 0,
                    "expiryTime": updated_expiry_time,
                    "enable": True,
                    "flow": "xtls-rprx-vision"
                }
            ]
        })
    }

    logger.info(f"[extend_client_key] PAYLOAD: {payload}")

    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

    try:
        async with session.post(f"{api_url}/panel/api/inbounds/updateClient/{client_uuid}",
                                json=payload, headers=headers) as response:
            print(f"[extend_client_key] user - [{telegram_id}] POST: {response.url} Status: {response.status}")
            print(f"[extend_client_key] user - [{telegram_id}] POST Request Data: {json.dumps(payload, indent=2)}")
            info = json.dumps(payload, indent=2)
            response_text = await response.text()
            print(f"[extend_client_key] user - [{telegram_id}] POST Response: {response_text}")

            if response.status == 200:
                return True
            else:
                logger.error(f"Ошибка при продлении ключа пользователя {telegram_id}: {response.status} - {response_text}")
                await notify_admin(text=f"Ошибка при продлении ключа пользователя {telegram_id}: {response.status} - {response_text}")
                return False
    except Exception as e:
        logger.error(f"Ошибка запроса у user {telegram_id}: {e}")
        return False


async def delete_client(session, server_id_name: str, client_id: str) -> bool:
    api_url = SERVER_ID[server_id_name]['url']
    url = f"{api_url}/panel/api/inbounds/1/delClient/{client_id}"
    headers = {
        'Accept': 'application/json'
    }

    try:
        async with session.post(url, headers=headers) as response:
            if response.status == 200:
                return True
            else:
                logger.error(f"[delete_client] Ошибка при удалении клиента {client_id}: {response.status} - {await response.text()}")
                await notify_admin(text=f"[delete_client] Ошибка при удалении клиента {client_id}: {response.status} - {await response.text()}")
                return False
    except Exception as e:
        logger.error(f"[delete_client] user {client_id}, Ошибка запроса: {e}")
        return False