from aiogram.types import Message, LabeledPrice
from logs.logging_config import logger


async def create_stars_payment(
    message: Message,
    price: int,
    description: str,
    payment_id: str
) -> bool:
    """
    Создает платеж в Stars
    :param message: Объект сообщения от пользователя
    :param price: Сумма в звездах (минимум 1)
    :param description: Описание платежа
    :param payment_id: Уникальный идентификатор (если не указан - создается автоматически)
    :return: True если платеж создан успешно
    """
    try:
        await message.answer_invoice(
            title="Оплата в Telegram",
            description=description,
            provider_token="",  # Для Stars обязательно пустая строка
            currency="XTR",
            prices=[LabeledPrice(label="Stars", amount=price)],
            payload=payment_id
        )
        return True
    except Exception as e:
        logger.error(f"Ошибка в создании платежа telegram_stars: {e}")
        return False

async def check_payment(update) -> bool:
    """
    Проверяет успешность платежа
    :param update: Объект update от Telegram
    :return: True если платеж успешный
    """
    return hasattr(update, 'message') and bool(update.message.successful_payment)