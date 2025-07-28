import asyncio
from _datetime import datetime
from api_3xui.Update_time_key import extend_time_key

async def main():
    telegram_id = 823524953
    server_id_name = "S1"
    client_uuid = "69e74353-adbd-488c-a06c-a27040d8b05a"
    limit_ip = 5
    # 📆 Укажи дату окончания подписки в читаемом виде
    expiry_time_str = "2025-09-14 18:15:58"  # Формат строго: YYYY-MM-DD HH:MM:SS


    # 🔄 Преобразуем в UNIX timestamp
    expiry_dt = datetime.strptime(expiry_time_str, "%Y-%m-%d %H:%M:%S")
    expiry_time = int(expiry_dt.timestamp() * 1000)
    print(f"🕒 Человеческое время: {expiry_dt}")
    print(f"🧮 UNIX timestamp: {expiry_time}")


    result = await extend_time_key(
        telegram_id=telegram_id,
        server_id_name=server_id_name,
        client_uuid=client_uuid,
        limit_ip=limit_ip,
        expiry_time=expiry_time
    )

    print("✅ Успешно!" if result else "❌ Ошибка!")

if __name__ == "__main__":
    asyncio.run(main())
