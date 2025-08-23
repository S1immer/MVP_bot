from data.loader import bot
from data.config import admins
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
from logs.logging_config import logger



async def notify_admin(text: str):
    """
    Отправка уведомлений админу с защитой от падений.
    """
    if isinstance(admins, (list, tuple)):
        for admin_id in admins:
            try:
                await bot.send_message(chat_id=admin_id, text=text)
            except TelegramForbiddenError:
                logger.info(f"❌ Админ {admin_id} заблокировал бота.")
            except TelegramBadRequest as e:
                logger.error(f"⚠️ Ошибка при отправке админу {admin_id}: {e}")
            except Exception as e:
                logger.error(f"⚠️ Неизвестная ошибка при отправке админу {admin_id}: {e}")
    else:
        try:
            await bot.send_message(chat_id=admins, text=text)
        except TelegramForbiddenError:
            logger.info(f"❌ Админ {admins} заблокировал бота.")
        except TelegramBadRequest as e:
            logger.error(f"⚠️ Ошибка при отправке лог-сообщения админу {admins}: {e}")
        except Exception as e:
            logger.error(f"⚠️ Неизвестная ошибка при отправке лог-сообщения админу {admins}: {e}")