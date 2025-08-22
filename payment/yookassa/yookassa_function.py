from uuid import uuid4
from yookassa import Payment
from payment.yookassa.config_yoo import RETURN_URL
from logs.logging_config import logger


async def create_payment(user_id, tariff_days, price, quantity_devices):
    """
    :param user_id: telegram_id пользователя
    :param tariff_days: количество дней int, для описания платежа
    :param price: цена int
    :param quantity_devices: количество устройств для описания платежа
    :return:
    """
    payment_id = str(uuid4())
    try:
        payment = Payment.create({
            "amount": {
                "value": f"{price}.00",
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": RETURN_URL
            },
            "capture": True,
            "description": f"Консультация сроком на {tariff_days} дней",
            "metadata": {
                "user_id": user_id,
                "tariff_date": tariff_days,
                "quantity_devices": quantity_devices,
                "payment_id": payment_id
            },
            "receipt": {
                "customer": {
                    "email": 'dan2412dan@mail.ru'
                },
                "items": [
                    {
                        "description": f"Консультация сроком на {tariff_days} дней",
                        "quantity": 1,
                        "amount": {
                            "value": f"{price}.00",
                            "currency": "RUB"
                        },
                        "vat_code": 1
                    }
                ]
            }
        })
        return payment.confirmation.confirmation_url, payment.id
    except Exception as e:
        logger.error(f"Ошибка создания платежа YooKassa: {e}")
        return None, None


async def check_payment_status(payment_id):
    try:
        payment = Payment.find_one(payment_id)  # Получаем объект платежа
        return payment.status  # Возвращаем только статус ('pending', 'succeeded' и т.д.)
    except Exception as e:
        print(f"Ошибка при проверке статуса платежа: {e}")
        return None