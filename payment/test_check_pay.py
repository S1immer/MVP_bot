import asyncio
from yookassa_function import create_payment, check_payment_status


async def chek():
    payment_id = "2f7c5dc0-000f-5000-b000-1bc8e43e0423"  # Подставь реальный ID платежа

    payment_status = await check_payment_status(payment_id)
    print(f"Payment Status: {payment_status}")

if __name__ == "__main__":
    asyncio.run(chek())
