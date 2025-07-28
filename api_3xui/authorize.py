import json
import aiohttp
# import asyncio
from data_servers.servers import SERVER_ID



session = None


async def login_with_credentials(server_name: str):
    """
    Авторизация на сервере.
    :param server_name: ' ', str - идентификатор сервера
    # :param username: str - имя пользователя
    # :param password: str - пароль
    :return: aiohttp.ClientSession - сессия с установленными куками
    """
    global session
    session = aiohttp.ClientSession()
    api_url = SERVER_ID[server_name]['url']
    auth_url = f"{api_url}/login/"

    username = SERVER_ID[server_name]['username']
    password = SERVER_ID[server_name]['password']


    data = {
        "username": username,
        "password": password
    }

    async with session.post(auth_url, json=data) as response:
        if response.status == 200:
            session.cookie_jar.update_cookies(response.cookies)
            # print(f"Куки после авторизации: {session.cookie_jar.filter_cookies(URL(auth_url))}")
            return session
        else:
            raise Exception(f"Ошибка авторизации: {response.status}, {await response.text()}")


# async def main():
#     server_name = 'S1'
#
#     auth = await login_with_credentials(server_name)
#     print(f"Авторизация прошла успешно")
#
#
# if __name__ == "__main__":
#     asyncio.run(main())



async def get_clients(session: aiohttp.ClientSession, server_id_name: str):
    """
    Получение списка клиентов.
    :param session: aiohttp.ClientSession - сессия для запроса
    :param server_id_name: str - идентификатор сервера
    :return: dict - ответ от сервера
    """
    api_url = SERVER_ID[server_id_name]['url']
    async with session.get(f'{api_url}/panel/api/inbounds/list/') as response:
        if response.status == 200:
            return await response.json()
        else:
            raise Exception(f"Ошибка при получении клиентов: {response.status}, {await response.text()}")


async def link(session: aiohttp.ClientSession, server_id_name: str, client_uuid: str, telegram_id: str):
    """
    Получение ссылки для подключения по ID клиента.
    :param session: aiohttp.ClientSession - сессия для запроса
    :param server_id_name: str - идентификатор сервера
    :param client_uuid: str - идентификатор клиента
    :param telegram_id: int - электронная почта клиента
    :return: str - ссылка для подключения
    """
    response = await get_clients(session, server_id_name)

    if 'obj' not in response or len(response['obj']) == 0:
        raise Exception("Не удалось получить данные клиентов.")

    inbounds = response['obj'][0]
    stream_settings = json.loads(inbounds['streamSettings'])
    tcp = stream_settings.get('network', 'tcp')
    reality = stream_settings.get('security', 'reality')
    flow = stream_settings.get('flow', 'xtls-rprx-vision')
    short_uuid = client_uuid[:5]

    key_vless = (
        f"vless://{client_uuid}@{SERVER_ID[server_id_name]['DOMEN']}:{SERVER_ID[server_id_name]['PORT']}?type={tcp}&security={reality}&pbk={SERVER_ID[server_id_name]['PBK']}"
        f"&fp=random&sni={SERVER_ID[server_id_name]['SNI']}&sid={SERVER_ID[server_id_name]['SID']}&spx=%2F&flow={flow}#{SERVER_ID[server_id_name]['PREFIX']} [{short_uuid}] [{telegram_id}]"
    )
    return key_vless


# async def main():
#     server_name = input("Введите идентификатор сервера (например, S1 или S2): ")
#
#     # Авторизация с использованием данных из server_id
#     session = await login_with_credentials(server_name, server_id[server_name]['username'],
#                                            server_id[server_name]['password'])
#
#     client_id = input("Введите идентификатор клиента: ")
#     email = input("Введите электронную почту клиента: ")
#
#     link_data = await link(session, server_name, client_uuid, telegram_id)
#
#     print("Ссылка для подключения:")
#     print(link_data)
#     await session.close()
#
#
# asyncio.run(main())