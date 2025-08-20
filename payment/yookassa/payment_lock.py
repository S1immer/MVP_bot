from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest, TelegramAPIError


# словарь разрешённых callback-данных для разных систем оплаты
ALLOWED_CALLBACKS = {
    "yookassa": ["check_payment_yookassa", "cancel_payment_yookassa"]
    # сюда можно добавлять новые системы
}


class PaymentLockMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        state: FSMContext = data.get("state")
        if not state:
            return await handler(event, data)

        user_data = await state.get_data()
        payment_id = user_data.get("payment_id")
        payment_message_id = user_data.get("payment_message_id")  # ID сообщения с платёжкой

        # если есть незавершённый платеж
        if payment_id and payment_message_id:
            # разрешаем только проверку/отмену платежа для любой системы
            if isinstance(event, CallbackQuery):
                if any(event.data in allowed for allowed in ALLOWED_CALLBACKS.values()):
                    return await handler(event, data)

            # блокируем всё остальное
            try:
                await event.bot.send_message(
                    chat_id=event.from_user.id,
                    text="⚠️ Сначала завершите текущий платёж!",
                    reply_to_message_id=payment_message_id
                )
                if isinstance(event, CallbackQuery):
                    await event.answer()  # убираем "часики" на кнопке
            except (TelegramBadRequest, TelegramAPIError):
                # если сообщение с платежом потерялось — показываем alert/ответ
                if isinstance(event, CallbackQuery):
                    await event.answer(text="⚠️ Сначала завершите текущий платёж!", show_alert=True)
                elif isinstance(event, Message):
                    await event.reply("⚠️ Сначала завершите текущий платёж!")

            return None  # блокируем дальнейшую обработку

        # если payment_id нет — продолжаем обработку
        return await handler(event, data)
