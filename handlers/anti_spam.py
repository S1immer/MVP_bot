from functools import wraps
from aiogram.types import Message, CallbackQuery
import asyncio
from typing import Union, Dict
from logs.logging_config import logger

USER_STATES: Dict[int, Dict[str, dict]] = {}


async def _remove_block(user_id: int, section: str, block_delay: int):
    await asyncio.sleep(block_delay)
    if user_id in USER_STATES and section in USER_STATES[user_id]:
        USER_STATES[user_id][section]['blocked'] = False
        logger.debug(f"Блокировка снята для user_id {user_id} в разделе {section}")


def anti_spam(
        warn_delay=2,  # Время между запросами до предупреждения (сек)
        block_delay=5,  # Время блокировки после спама (сек)
        message_text="🚫 Пожалуйста, не спамьте!",
        section="global"  # Группа кнопок для блокировки
):
    def decorator(func):
        @wraps(func)
        async def wrapper(obj: Union[Message, CallbackQuery], *args, **kwargs):
            user_id = obj.from_user.id

            # Инициализация состояния
            if user_id not in USER_STATES:
                USER_STATES[user_id] = {}
            if section not in USER_STATES[user_id]:
                USER_STATES[user_id][section] = {
                    'last_request': asyncio.get_event_loop().time() - warn_delay,
                    'blocked': False
                }

            state = USER_STATES[user_id][section]

            # Проверка активной блокировки
            if state['blocked']:
                return None  # Полный игнор при блокировке

            current_time = asyncio.get_event_loop().time()
            time_since_last = current_time - state['last_request']

            # Проверка слишком частых запросов
            if time_since_last < warn_delay:
                # Всегда показываем предупреждение
                if isinstance(obj, CallbackQuery):
                    await obj.answer(message_text, show_alert=True)
                else:
                    await obj.answer(message_text)

                # Активируем блокировку
                state['blocked'] = True
                asyncio.create_task(_remove_block(user_id, section, block_delay))
                return None

            # Нормальный запрос
            state['last_request'] = current_time

            try:
                return await func(obj, *args, **kwargs)
            except Exception as e:
                logger.error(f"Ошибка в обработчике: {e}")
                raise

        return wrapper

    return decorator