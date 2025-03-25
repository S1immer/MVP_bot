from uuid import uuid4
from scripts.get_least_loaded_server import get_least_loaded_server
from api_3xui.authorize import login_with_credentials, get_clients, link
from api_3xui.client import add_user
from data_servers.tariffs import tariffs
from data_servers.servers import server_id
from datetime import datetime, timedelta, timezone
import asyncio


session_global = None


async def key_trial(telegram_id: int, tariff_name: str):

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
        tariff_data = tariffs[tariff_name]
        trial_days = tariff_data['days']
        # print(f"Выбран тариф: {tariff_name}, дней: {trial_days}")

        # Вычисляем время истечения срока действия
        current_time = datetime.now(timezone.utc)
        expiry_time = current_time + timedelta(days=trial_days)
        expiry_timestamp = int(expiry_time.timestamp() * 1000)
        # print("Добавление клиента...")

        await add_user(
            session_global,
            server_id_name,
            client_uuid,
            telegram_id,
            2,
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
            session_global,  # Передаем global_session
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
# async def main():
#     telegram_id = 65233
#     tariff_name = 'year'  # Укажите название тарифа здесь
#     key = await key_trial(telegram_id, tariff_name)
#     if key:
#         print(f"Тестовый ключ: {key}")
#     else:
#         print("Не удалось получить тестовый ключ.")
#
#
# if __name__ == "__main__":
#     asyncio.run(main())
