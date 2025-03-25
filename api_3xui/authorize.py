import json


import aiohttp
from data_servers.servers import server_id

session_global = None


async def login_with_credentials(server_name: str, username: str, password: str):
    """
    Авторизация на сервере.
    :param server_name: ' ', str - идентификатор сервера
    :param username: str - имя пользователя
    :param password: str - пароль
    :return: aiohttp.ClientSession - сессия с установленными куками
    """
    global session_global
    session_global = aiohttp.ClientSession()
    api_url = server_id[server_name]['url']
    auth_url = f"{api_url}/login/"

    data = {
        "username": username,
        "password": password
    }

    async with session_global.post(auth_url, json=data) as response:
        if response.status == 200:
            session_global.cookie_jar.update_cookies(response.cookies)
            return session_global
        else:
            raise Exception(f"Ошибка авторизации: {response.status}, {await response.text()}")


async def get_clients(session: aiohttp.ClientSession, server_id_name: str):
    """
    Получение списка клиентов.
    :param session: aiohttp.ClientSession - сессия для запроса
    :param server_id_name: str - идентификатор сервера
    :return: dict - ответ от сервера
    """
    api_url = server_id[server_id_name]['url']
    async with session.get(f'{api_url}/panel/api/inbounds/list/') as response:
        if response.status == 200:
            return await response.json()
        else:
            raise Exception(f"Ошибка при получении клиентов: {response.status}, {await response.text()}")


async def link(session: aiohttp.ClientSession, server_id_name: str, client_id: str, email: str):
    """
    Получение ссылки для подключения по ID клиента.
    :param session: aiohttp.ClientSession - сессия для запроса
    :param server_id_name: str - идентификатор сервера
    :param client_id: str - идентификатор клиента
    :param email: str - электронная почта клиента
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

    key_vless = (
        f"vless://{client_id}@{server_id[server_id_name]['DOMEN']}{server_id[server_id_name]['PORT']}?type={tcp}&security={reality}&pbk={server_id[server_id_name]['PBK']}"
        f"&fp=random&sni={server_id[server_id_name]['SNI']}&sid={server_id[server_id_name]['SID']}&spx=%2F&flow={flow}#{server_id[server_id_name]['PREFIX']} [{email}]"
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
#     link_data = await link(session, server_name, client_id, email)
#
#     print("Ссылка для подключения:")
#     print(link_data)
#     await session.close()
#
#
# asyncio.run(main())