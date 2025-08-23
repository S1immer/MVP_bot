from aiogram import Router
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from handlers.admin_menu import clear_state_user
from data.config import admins  # список админов

admin_router = Router()
admin_router.include_router(clear_state_user.router)


@admin_router.message(Command("admin"))
async def admin_menu(message: Message):
    # Проверка: только админы могут видеть админку
    if message.from_user.id not in admins:
        await message.answer("❌ У вас нет доступа к админ-панели.")
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧹 Очистить состояние", callback_data="clear_state")],
        [InlineKeyboardButton(text="📅 Продлить срок подписки", callback_data="admin_extend_sub")],
        # Добавляйте другие кнопки по аналогии
    ])
    await message.answer(text="Админ-панель:", reply_markup=keyboard)
