import asyncio
from aiogram import Router
from aiogram.types import KeyboardButton, InlineKeyboardButton,ReplyKeyboardMarkup, InlineKeyboardMarkup, CallbackQuery
from api_3xui.tariff_key_generator import key_trial


router = Router()

# -----------------------------------
# 🔹 ФУНКЦИИ СОЗДАНИЯ КЛАВИАТУР
# -----------------------------------

async def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Создает основное меню (ReplyKeyboard)."""
    keyboard_layout = [
        [KeyboardButton(text='Остаток дней'), KeyboardButton(text='⚙️ Инструкция и 🔑 Ключ')],
        [KeyboardButton(text='💸 Оплатить подписку'), KeyboardButton(text='🤝 Реферальная система')],
        [KeyboardButton(text='📺 Канал'), KeyboardButton(text='🎁 Промокод')],
        [KeyboardButton(text='🆘 Помощь')],
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard_layout, resize_keyboard=True)

async def trial_button() -> InlineKeyboardMarkup:
    """Создает инлайн-кнопку для тестового периода."""
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text='🎁 Тестовый период', callback_data='trial')]]
    )

async def inline_price() -> InlineKeyboardMarkup:
    """Создает инлайн-кнопки с тарифами."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text='🔥 1 месяц - 199₽', callback_data='tariff_1_month')],
            [InlineKeyboardButton(text='🔥 3 месяца - 569₽', callback_data='tariff_3_months')],
            [InlineKeyboardButton(text='🔥 6 месяцев - 1099₽', callback_data='tariff_6_months')],
            [InlineKeyboardButton(text='🔥 12 месяцев - 2099₽', callback_data='tariff_12_months')],
        ]
    )





# -----------------------------------
# 🔹 ОБРАБОТЧИКИ CALLBACK-ЗАПРОСОВ
# -----------------------------------

async def trial_button_callback(query: CallbackQuery):
    """Обрабатывает запрос на получение тестового ключа."""
    telegram_id = query.from_user.id
    tariff_name = 'trial'

    key_data = await key_trial(telegram_id, tariff_name)

    if key_data:
        await query.answer(text="⏳Создание ключа...")
        await query.bot.send_message(chat_id=telegram_id, text="Ваш тестовый ключ ниже👇:")
        await query.bot.send_message(chat_id=telegram_id, text=f"```\n{key_data}\n```", parse_mode='MarkdownV2')
    else:
        await query.answer(text="Не удалось сформировать тестовый ключ.")

# Регистрация обработчика callback-запроса для тестового периода
@router.callback_query(lambda query: query.data == 'trial')
async def trial_button_callback_handler(query: CallbackQuery):
    await trial_button_callback(query)
