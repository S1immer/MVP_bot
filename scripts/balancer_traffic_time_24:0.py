import asyncio
import requests
from data_servers.servers import SERVER_ID
from database.DB_CONN_async import Session_db
from database.models_sql_async import Trafficdata
from sqlalchemy import select, update, insert
from sqlalchemy.exc import SQLAlchemyError



def bytes_to_gb(byte_value):
    return byte_value / (1024 ** 3)

""""
Каждые сутки записывается трафик в таблицу Trafficdata и обнуляется на серверах
"""


async def main():
    async with Session_db() as session:
        for server_key, server_info in SERVER_ID.items():
            print(f"Обрабатываем сервер {server_key}...")

            try:
                login_url = f"{server_info['url']}/login"
                traffic_url = f"{server_info['url']}/panel/api/inbounds/get/1"
                reset_traffic_url = f"{server_info['url']}/panel/api/inbounds/resetAllTraffics"

                username = server_info["username"]
                password = server_info["password"]

                http_session = requests.Session()
                login_data = {'username': username, 'password': password}
                headers = {'Accept': 'application/json'}

                response = http_session.post(login_url, data=login_data, headers=headers)
                response.raise_for_status()

                if response.status_code == 200:
                    print(f"Авторизация на сервере {server_key} прошла успешно!")
                    traffic_response = http_session.get(traffic_url, headers=headers)

                    if traffic_response.status_code == 200:
                        traffic_data = traffic_response.json()
                        up_traffic = traffic_data['obj']['up']
                        down_traffic = traffic_data['obj']['down']
                        total_traffic = up_traffic + down_traffic
                        traffic_gb = round(bytes_to_gb(total_traffic), 2)

                        print(f"Трафик для {server_key}: {traffic_gb} GB")

                        # Проверка и обновление / вставка данных
                        result = await session.execute(select(Trafficdata).where(Trafficdata.server_name == str(server_key)))
                        existing = result.scalars().first()
                        country = server_info.get("country", "unknown")

                        if existing:
                            await session.execute(
                                update(Trafficdata)
                                .where(Trafficdata.server_name == str(server_key))
                                .values(traffic=traffic_gb)
                            )
                            print(f"Обновлен трафик для {server_key}")
                        else:
                            await session.execute(
                                insert(Trafficdata).values(
                                    name_country=country,
                                    server_name=server_key,
                                    traffic=traffic_gb)
                            )
                            print(f"Добавлен трафик для {server_key}")

                        await session.commit()

                        reset_response = http_session.post(reset_traffic_url, headers=headers)
                        if reset_response.status_code == 200:
                            print(f"Трафик для {server_key} успешно сброшен!")
                        else:
                            print(f"Ошибка при сбросе трафика для {server_key}: {reset_response.status_code}")
                    else:
                        print(f"Ошибка при получении трафика: {traffic_response.status_code}")

            except requests.exceptions.RequestException as e:
                print(f"Ошибка при запросе {server_key}: {e}")
                continue
            except SQLAlchemyError as e:
                await session.rollback()
                print(f"Ошибка БД: {e}")
                continue
            except Exception as e:
                print(f"Неизвестная ошибка: {e}")
                continue


if __name__ == "__main__":
    asyncio.run(main())
