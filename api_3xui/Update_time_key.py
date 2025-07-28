from api_3xui.authorize import login_with_credentials
from api_3xui.client import extend_client_key



async def extend_time_key(telegram_id: int, server_id_name: str, client_uuid: str, limit_ip: int, expiry_time: int):
    """
    Продление/обновление подписки

    :param telegram_id: telegram_id пользователя
    :param server_id_name: сервер на котором сделать продление
    :param client_uuid: uuid4 пользователя
    :param limit_ip: количество устройств
    :param expiry_time: Формат UNIX Timestamp в милисекундах
    :return:
    """

    session = None

    try:
        session = await login_with_credentials(server_id_name)
        result = await extend_client_key(session, server_id_name=server_id_name, client_uuid=client_uuid,
                                limit_ip=limit_ip, telegram_id=telegram_id, new_expiry_time=expiry_time)

        return result
    except Exception as e:
        print(f'Error {e}')
        return False
    finally:
        if session:
            await session.close()