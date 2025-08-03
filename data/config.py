from dotenv import load_dotenv
import os

load_dotenv()  # Загружаем переменные окружения из .env

token = os.getenv('TOKEN')
if not token:
    raise RuntimeError("TOKEN не найден в переменных окружения")

admins = [823524953]