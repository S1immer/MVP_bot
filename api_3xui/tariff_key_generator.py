import asyncio
from uuid import uuid4
from scripts.get_least_loaded_server import get_least_loaded_server
from api_3xui.authorize import login_with_credentials, get_clients, link
from api_3xui.client import add_user
from data_servers.tariffs import tariffs_data
from data_servers.servers import server_id
from datetime import datetime, timedelta, timezone


session_global = None


async def key_generation(telegram_id: str, period: str, devices: str):

    server_id_name = get_least_loaded_server()
    # print(f"Наименее загруженный сервер: {server_id_name}")

    global session_global

    try:
        # Проверка существующей сессии
        if session_global is None:
            print("Сессия отсутствует. Авторизация...")
            session_global = await login_with_credentials(
                server_id_name,
                server_id[server_id_name]['username'],
                server_id[server_id_name]['password']
            )
            # print("Авторизация успешна")
        else:
            try:
                # Простой запрос для проверки активности сессии
                await session_global.get(server_id[server_id_name]['url'])
                print("Используется существующая сессия")
            except Exception as e:
                print(f"Сессия неактивна: {e}. Создаем новую...")
                session_global = await login_with_credentials(
                    server_id_name,
                    server_id[server_id_name]['username'],
                    server_id[server_id_name]['password']
                )
                print("Авторизация успешна")

        client_uuid = str(uuid4())
        # print(f"Сгенерированный UUID: {client_uuid}")

        # Получаем данные о тарифе
        tariff_data = tariffs_data[period][devices]
        tariff_days = tariff_data['days']
        device = tariff_data['device_limit']
        print(f"Выбран тариф: {period}, {device}, дней: {tariff_days}")

        # Вычисляем время истечения срока действия
        current_time = datetime.now(timezone.utc)
        expiry_time = current_time + timedelta(days=tariff_days)
        expiry_timestamp = int(expiry_time.timestamp() * 1000)
        # print("Добавление клиента...")

        await add_user(
            session_global,
            server_id_name,
            client_uuid,
            str(telegram_id),
            device,
            0,
            expiry_timestamp,
            True,
            'xtls-rprx-vision'
        )
        # print("Клиент добавлен")

        # print("Получение данных клиента...")
        response = await get_clients(session_global, server_id_name)  # Передаем global_session
        # print("Данные клиента получены")

        if 'obj' not in response or len(response['obj']) == 0:
            print("Не удалось получить данные клиентов.")
            return None

        # print("Формирование ключа...")
        link_data = await link(
            session_global,
            server_id_name,
            client_uuid,
            str(telegram_id)
        )
        # print("Ключ сформирован")

        return link_data

    except Exception as e:
        print(f"Произошла ошибка: {e}")
        return None


# Тестирование функции
async def main():
    telegram_id = str(3245615)
    period = 'six_months'
    devices = '5_devices'

    key = await key_generation(telegram_id, period, devices)
    if key:
        print(f"Тестовый ключ: {key}")
    else:
        print("Не удалось получить тестовый ключ.")


if __name__ == "__main__":
    asyncio.run(main())
