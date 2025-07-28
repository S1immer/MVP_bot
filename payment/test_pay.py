import asyncio
from yookassa_function import create_payment, check_payment_status

async def main():
    user_id = 12345
    tariff_date = 30 #"2025-03-28"
    price = 100  # Сумма в рублях
    quantity_devices = 1


    confirmation_url, payment_id = await create_payment(user_id, tariff_date, price, quantity_devices)
    print(f"Confirmation URL: {confirmation_url}")
    print(f"Payment ID: {payment_id}")


if __name__ == "__main__":
    asyncio.run(main())





#
# async def chek():
#     payment_id = "2f799f84-000f-5000-9000-16dae11fc45b"  # Подставь реальный ID платежа
#
#     payment_status = await check_payment_status(payment_id)
#     print(f"Payment Status: {payment_status}")
#
# if __name__ == "__main__":
#     asyncio.run(chek())

