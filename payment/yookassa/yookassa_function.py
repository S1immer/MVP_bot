from uuid import uuid4
from yookassa import Payment
from payment.yookassa.config_yoo import RETURN_URL


async def create_payment(user_id, tariff_date, price, quantity_devices):
    payment_id = str(uuid4())

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
        "description": f"Консультация сроком на {tariff_date} дней",
        "metadata": {
            "user_id": user_id,
            "tariff_date": tariff_date,
            "quantity_devices": quantity_devices,
            "payment_id": payment_id
        },
        "receipt": {
            "customer": {
                "email": 'dan2412dan@mail.ru'
            },
            "items": [
                {
                    "description": f"Консультация сроком на {tariff_date} дней",
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

    # print(f"Платеж успешно создан. confirmation_url={payment.confirmation.confirmation_url}, id={payment.id}")

    return payment.confirmation.confirmation_url, payment.id


async def check_payment_status(payment_id):
    try:
        payment = Payment.find_one(payment_id)  # Получаем объект платежа
        # print(f"Полный ответ платежной системы: {payment}")  # Логируем весь объект
        return payment['status']  # Возвращаем только статус ('pending', 'succeeded' и т.д.)
    except Exception as e:
        print(f"Ошибка при проверке статуса платежа: {e}")
        return None






# async def check_payment_status(payment_id):
#     payment = Payment.find_one(payment_id)
#
#     if payment.status == 'succeeded':
#         gb_limit = payment.metadata.get('gb_limit')
#
#         if gb_limit is None:
#             raise ValueError("Лимит данных не найден в метаданных платежа.")
#
#         try:
#             gb_limit = int(gb_limit)
#         except ValueError:
#             raise ValueError(f"Невозможно преобразовать лимит данных в целое число: {gb_limit}")
#
#         months = data_limit_to_months.get(gb_limit)
#         if months is None:
#             raise ValueError(f"Неизвестный лимит данных: {gb_limit}")
#
#         return True, gb_limit, months
#
#     elif payment.status == 'canceled':
#         return False, None, None

    # return False, None, None