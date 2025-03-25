import psycopg2
import requests
from data_servers.servers import server_id
from DB_CONN import connect_to_db

# Функция для конвертации байт в гигабайты
def bytes_to_gb(byte_value):
    return byte_value / (1024 ** 3)  # Переводим байты в гигабайты

# Получаем соединение с базой данных
conn = connect_to_db()

if conn:
    cursor = conn.cursor()
else:
    print("Не удалось подключиться к базе данных")
    exit()  # Выход из скрипта, если подключение не удалось

# Обрабатываем все сервера из server_id
for server_key, server_info in server_id.items():
    print(f"Обрабатываем сервер {server_key}...")

    try:
        # URL для авторизации и получения данных
        login_url = f"{server_info['url']}/login"
        traffic_url = f"{server_info['url']}/panel/api/inbounds/get/1"
        reset_traffic_url = f"{server_info['url']}/panel/api/inbounds/resetAllTraffics"

        # Логин и пароль
        username = server_info["username"]
        password = server_info["password"]

        # Создаем сессию
        session = requests.Session()

        # Данные для POST-запроса на авторизацию
        login_data = {
            'username': username,
            'password': password
        }

        # Заголовки, чтобы запрос был принят сервером как обычный веб-запрос
        headers = {
            'Accept': 'application/json',  # Указываем, что мы ожидаем JSON в ответ
        }

        # Выполняем POST-запрос на авторизацию
        response = session.post(login_url, data=login_data, headers=headers)

        # Проверяем статус ответа
        response.raise_for_status()  # Генерирует исключение для статусов 4xx и 5xx

        if response.status_code == 200:
            print(f"Авторизация на сервере {server_key} прошла успешно!")
            print("Ответ от сервера:", response.json())  # Выводим ответ от сервера

            # После успешной авторизации получаем трафик
            traffic_response = session.get(traffic_url, headers=headers)

            if traffic_response.status_code == 200:
                # Парсим ответ сервера и суммируем трафик
                traffic_data = traffic_response.json()
                up_traffic = traffic_data['obj']['up']
                down_traffic = traffic_data['obj']['down']
                total_traffic = up_traffic + down_traffic

                # Конвертируем трафик в гигабайты и округляем до 2 знаков
                traffic_gb = round(bytes_to_gb(total_traffic), 2)

                print(f"Трафик для {server_key}: {traffic_gb} GB")

                # Проверяем, есть ли сервер в базе данных
                cursor.execute('SELECT id FROM traffic_data WHERE server_name = %s', (server_key,))
                result = cursor.fetchone()

                if result:
                    # Если сервер существует, обновляем трафик
                    cursor.execute('''
                        UPDATE traffic_data
                        SET traffic = %s
                        WHERE server_name = %s
                    ''', (traffic_gb, server_key))
                    print(f"Трафик для {server_key} обновлен в базе данных.")
                else:
                    # Если сервера нет в базе данных, вставляем новую запись
                    cursor.execute('''
                        INSERT INTO traffic_data (server_name, traffic)
                        VALUES (%s, %s)
                    ''', (server_key, traffic_gb))
                    print(f"Трафик для {server_key} добавлен в базу данных.")

                conn.commit()

                # Сбрасываем трафик на сервере
                reset_response = session.post(reset_traffic_url, headers=headers)

                if reset_response.status_code == 200:
                    print(f"Трафик для {server_key} успешно сброшен!")
                else:
                    print(f"Ошибка при сбросе трафика для {server_key}: {reset_response.status_code}")

            else:
                print(f"Ошибка при получении трафика для {server_key}: {traffic_response.status_code}")

        else:
            print(f"Ошибка авторизации для {server_key}: {response.status_code}")

    except requests.exceptions.RequestException as e:
        print(f"Ошибка при запросе для {server_key}: {e}")
        print(f"Пропускаем сервер {server_key}...")
        continue

    except psycopg2.Error as e:
        print(f"Ошибка при работе с базой данных для {server_key}: {e}")
        print(f"Пропускаем сервер {server_key}...")
        continue

    except Exception as e:
        print(f"Неизвестная ошибка для {server_key}: {e}")
        print(f"Пропускаем сервер {server_key}...")
        continue

# Закрываем соединение с базой данных
if conn:
    conn.close()
