import asyncio
import json
import uuid
# import aiohttp
# from aiohttp import BasicAuth
from datetime import datetime, timedelta, timezone
from data_servers.servers import SERVER_ID
from api_3xui.authorize import login_with_credentials
from data_servers.tariffs import tariffs


async def add_user(session, server_id_name: str, client_uuid: str, telegram_id: int, limit_ip: int, total_gb: int, expiry_time: int, enable: bool, flow: str):
    """
    Добавляет пользователя в веб-панель 3X-UI.
    """

    server = SERVER_ID[server_id_name]
    api_url = server['url']
    url = f'{api_url}/panel/api/inbounds/addClient'

    client_data = {
        "id": client_uuid,
        "email": str(telegram_id),  # Важно преобразовать в строку
        "limitIp": limit_ip,
        "totalGB": total_gb,
        "expiryTime": expiry_time,
        "enable": enable,
        "flow": flow
    }

    settings = json.dumps({
        "clients": [client_data]
    })

    data = {
        "id": 1,
        "settings": settings
    }

    headers = {
        'Content-Type': 'application/json',
    }

    # Вывод JSON для проверки
    print("\nJSON для отправки (data):")
    print(json.dumps(data, indent=4))

    try:
        auth = (server['username'], server['password'])
        async with session.post(url,auth=auth, json=data, headers=headers) as response:
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
    except Exception as e:
        print(f"Произошла ошибка при отправке запроса: {e}")
        return None


async def main():
    # Входные данные для теста (измените эти значения)
    telegram_id = 123465352  # Замените на нужный Telegram ID
    server_id_name = "S2"  # Замените на ID нужного сервера
    tariff_name = "trial"  # Замените на название тарифа из tariffs.py

    client_uuid = str(uuid.uuid4())
    limit_ip = 2
    total_gb = 0
    enable = True
    flow = 'xtls-rprx-vision'  # Оставляем пустой, как в примере

    # Получаем количество дней из tariffs.py
    if tariff_name in tariffs:
        trial_days = tariffs[tariff_name]['days']
        print(f"Дней для тарифа '{tariff_name}': {trial_days}")  # Добавлено для отладки
    else:
        print(f"Ошибка: Тариф '{tariff_name}' не найден в tariffs.py.")
        return

    # Проверка типа данных trial_days
    if not isinstance(trial_days, int):
        print(f"Ошибка: trial_days должно быть целым числом.  Текущий тип: {type(trial_days)}")
        return

    # Расчет expiry_time (используем пример с миллисекундами)
    current_time = datetime.now(timezone.utc)
    expiry_time = current_time + timedelta(days=trial_days)
    expiry_timestamp = int(expiry_time.timestamp() * 1000)

    print(f"Срок действия подписки (timestamp): {expiry_timestamp}")

    # Пример использования (предполагается, что server_id определен в data_servers/servers.py)
    if server_id_name not in SERVER_ID:
        print(f"Ошибка: Сервер с ID '{server_id_name}' не найден в server_id.")
        return

    # Авторизуемся на сервере
    try:
        session = await login_with_credentials(server_id_name, SERVER_ID[server_id_name]['username'], SERVER_ID[server_id_name]['password'])
        print("Авторизация успешна")
    except Exception as e:
        print(f"Ошибка авторизации: {e}")
        return

    try:
        result = await add_user(session, server_id_name, client_uuid, telegram_id, limit_ip, total_gb, expiry_timestamp, enable, flow)

        if result:
            print("Успешно добавлено:", result)
        else:
            print("Не удалось добавить пользователя.")
    finally:
        # Закрываем сессию
        await session.close()


if __name__ == "__main__":
    asyncio.run(main())
