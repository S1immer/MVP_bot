import asyncio
import requests
from data_servers.servers import SERVER_ID
from database.DB_CONN_async import Session_db
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from logs.logging_config import logger
from logs.admin_notify import notify_admin


def bytes_to_gb(byte_value):
    return byte_value / (1024 ** 3)


""""
Каждые сутки записывается трафик в таблицу Trafficdata и обнуляется на серверах
"""


async def main():
    async with Session_db() as session:
        for server_key, server_info in SERVER_ID.items():
            http_session = None

            try:
                login_url = f"{server_info['url']}/login"
                traffic_url = f"{server_info['url']}/panel/api/inbounds/get/1"
                reset_traffic_url = f"{server_info['url']}/panel/api/inbounds/resetAllTraffics"

                username = server_info["username"]
                password = server_info["password"]
                country = server_info.get("country", "unknown")  # Получаем country здесь!

                http_session = requests.Session()
                login_data = {
                    'username': username,
                    'password': password
                }
                headers = {'Accept': 'application/json'}

                # Авторизация
                response = http_session.post(login_url, data=login_data, headers=headers)
                response.raise_for_status()

                if response.status_code == 200:

                    # Получение трафика
                    traffic_response = http_session.get(traffic_url, headers=headers)

                    if traffic_response.status_code == 200:
                        traffic_data = traffic_response.json()
                        up_traffic = traffic_data['obj']['up']
                        down_traffic = traffic_data['obj']['down']
                        total_traffic = up_traffic + down_traffic
                        traffic_gb = round(bytes_to_gb(total_traffic), 2)

                        # Проверка и обновление / вставка данных
                        result = await session.execute(
                            text("SELECT * FROM traffic_data WHERE server_name = :server_name"),
                            {"server_name": str(server_key)}
                        )
                        existing = result.first()

                        if existing:
                            await session.execute(
                                text("UPDATE traffic_data SET traffic = :traffic WHERE server_name = :server_name"),
                                {"traffic": traffic_gb, "server_name": str(server_key)}
                            )
                        else:
                            await session.execute(
                                text(
                                    "INSERT INTO traffic_data (name_country, server_name, traffic, quantity_users) VALUES (:country, :server_name, :traffic, :quantity_users)"),
                                {"country": country, "server_name": str(server_key), "traffic": traffic_gb, "quantity_users": 0}
                            )

                        await session.commit()

                        # Сброс трафика
                        reset_response = http_session.post(reset_traffic_url, headers=headers)
                        if reset_response.status_code == 200:
                            logger.info(f"[balancer_traffic] Трафик для {server_key} успешно сброшен!")
                        else:
                            logger.error(f"[balancer_traffic] Ошибка при сбросе трафика для {server_key}: {reset_response.status_code}")
                            await notify_admin(text=f"[balancer_traffic] Ошибка при сбросе трафика для {server_key}!\n"
                                                    f"Ошибка: {reset_response.status_code}")
                    else:
                        logger.error(f"[balancer_traffic] Ошибка при получении трафика на {server_key}: {traffic_response.status_code}")
                        await notify_admin(text=f"[balancer_traffic] Ошибка при получении трафика на {server_key}!\n"
                                                f"Ошибка: {traffic_response.status_code}")
                else:
                    logger.error(f"[balancer_traffic] Ошибка авторизации на {server_key}: {response.status_code}")
                    await notify_admin(text=f"[balancer_traffic] Ошибка авторизации на {login_url}\n"
                                            f"Ошибка: {response.status_code}")

            except requests.exceptions.RequestException as e:
                logger.error(f"[balancer_traffic] Ошибка при запросе {server_key}: {e}")
                await notify_admin(text=f"[balancer_traffic] Ошибка при запросе {server_key}!\n"
                                        f"Ошибка: {e}")
                continue
            except SQLAlchemyError as e:
                await session.rollback()
                logger.info(f"[balancer_traffic] Ошибка БД: {e}")
                await notify_admin(text=f"[balancer_traffic] Ошибка БД: {e}")
                continue
            except Exception as e:
                logger.info(f"[balancer_traffic] Неизвестная ошибка на сервере {server_key}: {e}")
                await notify_admin(text=f"[balancer_traffic] Неизвестная ошибка на сервере {server_key}!\n"
                                        f"Ошибка: {e}")
                continue
            finally:
                if http_session:
                    http_session.close()


if __name__ == "__main__":
    asyncio.run(main())