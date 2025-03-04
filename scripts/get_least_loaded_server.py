import sqlite3

def get_least_loaded_server():
    conn = sqlite3.connect('../database/traffic.db')
    cursor = conn.cursor()

    cursor.execute("SELECT server_name, traffic_data FROM traffic_logs")
    servers_traffic = cursor.fetchall()

    conn.close()

    least_loaded_server = min(servers_traffic, key=lambda x: x[1])
    return least_loaded_server[0]  # Возвращает имя сервера
