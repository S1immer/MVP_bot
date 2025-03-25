import json
from data_servers.servers import server_id


async def add_user(session, server_id_name: str, client_uuid: str, telegram_id: int, limit_ip: int, total_gb: int, expiry_time: int, enable: bool, flow: str):
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

    server = server_id[server_id_name]
    api_url = server['url']
    url = f'{api_url}/panel/api/inbounds/addClient'


    client_data = {
        "id": client_uuid,
        "email": str(telegram_id),
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
        print(f"Запрос на добавление пользователя: {data}")
        print(f"Статус ответа: {response.status}")
        response_text = await response.text()
        print(f"Ответ от сервера: {response_text}")

        if response.status == 200:
            print(f"Пользователь добавлен: uuid={client_uuid}")
            return await response.json()
        else:
            print(f"Ошибка при добавлении пользователя: {response.status}, {response_text}")
            return None

# # Пример использования
# async def main():
#     import aiohttp
#     async with aiohttp.ClientSession() as session:
#         await add_user(session, "S1", "client_uuid", "tg_id", 2, 0, 0, True, "xtls-rprx-vision")
#
# import asyncio
# asyncio.run(main())


async def extend_client_key(session, server_id_name: str, client_uuid: str, email: int,
                            new_expiry_time: int) -> bool:
    """
    Расширяет подписку существующего клиента в веб-панели 3X-UI.

    :param session: Сессия для запроса
    :param server_id_name: ID сервера
    :param client_uuid: Уникальный идентификатор клиента
    :param email: telegram_id клиента
    :param new_expiry_time: Новая дата истечения срока действия подписки
    :return: True если операция успешна, False в случае ошибки
    """
    server = server_id[server_id_name]
    api_url = server['url']

    async with session.get(f"{api_url}/panel/api/inbounds/getClientTraffics/{email}",
                           auth=(server['username'], server['password'])) as get_response:
        print(f"GET {get_response.url} Status: {get_response.status}")
        response_text = await get_response.text()
        print(f"GET Response: {response_text}")

        if get_response.status != 200:
            print(f"Ошибка при получении данных клиента: {get_response.status} - {response_text}")
            return False

        client_data = (await get_response.json()).get("obj", {})
        print(client_data)

        if not client_data:
            print("Не удалось получить данные клиента.")
            return False

        current_expiry_time = client_data.get('expiryTime', 0)

        if current_expiry_time == 0:
            current_expiry_time = new_expiry_time

        updated_expiry_time = max(current_expiry_time, new_expiry_time)

        payload = {
            "id": 1,
            "settings": json.dumps({
                "clients": [
                    {
                        "id": client_uuid,
                        "alterId": 0,
                        "email": email,
                        "limitIp": 2,
                        "totalGB": 0,
                        "expiryTime": updated_expiry_time,
                        "enable": True,
                        "flow": "xtls-rprx-vision"
                    }
                ]
            })
        }

        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

        try:
            async with session.post(f"{api_url}/panel/api/inbounds/updateClient/{client_uuid}", json=payload,
                                    headers=headers, auth=(server['username'], server['password'])) as response:
                print(f"POST {response.url} Status: {response.status}")
                print(f"POST Request Data: {json.dumps(payload, indent=2)}")
                response_text = await response.text()
                print(f"POST Response: {response_text}")

                if response.status == 200:
                    return True
                else:
                    print(f"Ошибка при продлении ключа: {response.status} - {response_text}")
                    return False
        except Exception as e:
            print(f"Ошибка запроса: {e}")
            return False

# # Пример использования
# async def main():
#     import aiohttp
#     async with aiohttp.ClientSession() as session:
#         await extend_client_key(session, "S1", "uuid", "email", 1643723400)
#
# import asyncio
# asyncio.run(main())


async def delete_client(session, server_id_name: str, client_id: str) -> bool:
    api_url = server_id[server_id_name]['url']
    url = f"{api_url}/panel/api/inbounds/1/delClient/{client_id}"
    headers = {
        'Accept': 'application/json'
    }

    try:
        async with session.post(url, headers=headers) as response:
            if response.status == 200:
                return True
            else:
                print(f"Ошибка при удалении клиента: {response.status} - {await response.text()}")
                return False
    except Exception as e:
        print(f"Ошибка запроса: {e}")
        return False