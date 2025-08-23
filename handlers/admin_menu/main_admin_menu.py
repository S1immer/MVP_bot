from aiogram import Router
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from handlers.admin_menu.add_new_servers import router as add_new_servers_router
from handlers.admin_menu.clear_state_user import router as clear_state_router
from handlers.admin_menu.extend_sub_user import router as extend_sub_router
from data.config import admins  # список админов

admin_router = Router()

admin_router.include_router(clear_state_router)
admin_router.include_router(add_new_servers_router)
admin_router.include_router(extend_sub_router)

@admin_router.message(Command("admin"))
async def admin_menu(message: Message):
    # Проверка: только админы могут видеть админку
    if message.from_user.id not in admins:
        await message.answer("❌ У вас нет доступа к админ-панели.")
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧹 Очистить состояние", callback_data="clear_state")],
        [InlineKeyboardButton(text="📅 Продлить подписку", callback_data="admin_extend_sub")],
        [InlineKeyboardButton(text="🖥️ Добавить новые сервера", callback_data="add_new_servers")],
    ])
    await message.answer(text="Админ-панель:", reply_markup=keyboard)
