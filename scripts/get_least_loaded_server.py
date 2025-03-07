import psycopg2
from database.DB_CONN import connect_to_db


def get_least_loaded_server():
    conn = connect_to_db()

    if conn:
        cursor = conn.cursor()

        cursor.execute("SELECT server_name, traffic FROM traffic_data")
        servers_traffic = cursor.fetchall()

        conn.close()

        if servers_traffic:
            least_loaded_server = min(servers_traffic, key=lambda x: x[1])
            return least_loaded_server[0]  # Возвращает имя сервера
        else:
            print("Нет данных о серверах")
            return None
    else:
        print("Не удалось подключиться к базе данных")
        return None
