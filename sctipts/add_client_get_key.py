import requests
import json
import logging
import uuid
from servers import login  # Импортируем данные о серверах
from urllib.parse import urlparse  # Для разбора URL

# Настройка логирования
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# Выберите сервер (например, S1 или S2)
selected_server = login["S1"]  # Здесь можно выбрать нужный сервер (например, S1)

# URL для авторизации и получения данных
login_url = f"{selected_server['url']}/login"
data_url = f"{selected_server['url']}/panel/api/inbounds/get/1"  # Исправлено на правильный URL
add_client_url = f"{selected_server['url']}/panel/api/inbounds/addClient"

# Логин и пароль
username = selected_server['username']
password = selected_server['password']

# Ваш Telegram ID (замените на свой)
telegram_id = "Ваш_Telegram_ID_TEST"  # Например: "-1001552213809"

# Создаем сессию
session = requests.Session()

# Данные для POST-запроса на авторизацию
login_data = {
    'username': username,
    'password': password
}

# Заголовки для авторизации
headers = {
    'Accept': 'application/json',
}

# Извлечение IP или домена из URL
parsed_url = urlparse(selected_server['url'])
listening_ip_or_domain = parsed_url.netloc.split(':')[0]  # Получаем netloc, затем убираем порт, если есть


# Функция для генерации уникального UUID
def generate_uuid():
    return str(uuid.uuid4())


# Шаг 1: Авторизация
try:
    response = session.post(login_url, data=login_data, headers=headers)
    response.raise_for_status()  # Генерирует исключение для статусов 4xx и 5xx

    if response.status_code == 200:
        print("Авторизация прошла успешно!")

        # Шаг 2: Генерация нового UUID для клиента
        new_client_uuid = generate_uuid()
        print(f"Генерирован новый UUID для клиента: {new_client_uuid}")

        # Шаг 3: Создание клиента с использованием Telegram ID в поле email и нового UUID
        new_client_data = {
            "id": 1,  # ID входящего трафика
            "settings": json.dumps({
                "clients": [{
                    "id": new_client_uuid,  # Используем новый UUID
                    "flow": "xtls-rprx-vision",
                    "email": telegram_id,  # Записываем Telegram ID вместо email
                    "limitIp": 0,
                    "totalGB": 0,
                    "expiryTime": 0,
                    "enable": True,
                    "tgId": "",
                    "subId": "",  # Можно оставить пустым или указать значение
                    "reset": 0
                }]
            })
        }

        # Выполняем POST-запрос для добавления клиента
        add_client_response = session.post(add_client_url, json=new_client_data, headers=headers)
        add_client_response.raise_for_status()

        if add_client_response.status_code == 200:
            print(f"Клиент успешно добавлен с ID: {new_client_uuid}")

            # Шаг 4: Получение данных о клиенте по адресу data_url
            response = session.get(data_url, headers=headers)
            response.raise_for_status()
            inbound_data = response.json()

            if inbound_data.get("success"):
                inbound_data_updated = inbound_data['obj']

                # Печатаем streamSettings для отладки, чтобы понять его структуру
                print("streamSettings:", inbound_data_updated.get('streamSettings'))

                # Проверяем, является ли streamSettings строкой (возможно, строка JSON)
                stream_settings = inbound_data_updated.get('streamSettings')

                if isinstance(stream_settings, str):
                    # Если streamSettings — это строка, нужно ее распарсить
                    stream_settings = json.loads(stream_settings)

                # Печатаем распарсенные streamSettings для отладки
                print("Parsed streamSettings:", stream_settings)

                # Извлекаем необходимые данные из streamSettings
                if stream_settings:
                    reality_settings = stream_settings.get('realitySettings', {})
                    public_key = reality_settings.get('settings', {}).get('publicKey', '')
                    sni_list = reality_settings.get('serverNames', [])

                    # Извлекаем только первый SNI и другие параметры для формирования ключа
                    sni = sni_list[0] if sni_list else ""

                    # Извлекаем порт из данных инбоуда
                    port = inbound_data_updated.get('port', '443')  # Порт (по умолчанию 443)
                    remark_name = inbound_data_updated.get('remark', 'Примечание для id 1')

                    # Получаем ID клиента из настроек (UUID клиента из панели)
                    client_uuid = new_client_uuid  # Используем UUID, который мы только что создали

                    # Получаем sid (это первое значение в shortIds)
                    sid = reality_settings.get('shortIds', [])[0] if reality_settings.get('shortIds') else ''

                    # Шаг 5: Формирование ключа в нужном формате
                    key_format = f"vless://{client_uuid}@{listening_ip_or_domain}:{port}?type=tcp&security=reality&pbk={public_key}&fp=random&sni={sni}&sid={sid}&spx=%2F&flow=xtls-rprx-vision#{remark_name} [{telegram_id}]"
                    print("Сформированный ключ:", key_format)

                else:
                    print("Ошибка: streamSettings не содержат данных или имеют некорректный формат.")
            else:
                print("Ошибка получения данных:", inbound_data.get("msg"))

        else:
            print("Ошибка при добавлении клиента:", add_client_response.json().get("msg"))

    else:
        print("Ошибка авторизации:", response.json().get("msg"))

except requests.exceptions.HTTPError as err:
    if err.response.status_code == 404:
        print("Ошибка 404: Ресурс не найден.")
        logger.warning("Получена ошибка 404 для URL: %s", login_url)
    else:
        print(f"Ошибка HTTP: {err}")
except requests.exceptions.RequestException as e:
    print(f"Ошибка при запросе: {e}")
