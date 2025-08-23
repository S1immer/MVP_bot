from aiogram import Router, F
from aiogram.types import CallbackQuery
from data.config import admins
from database.functions_db_async import sync_servers_to_db
from logs.logging_config import logger
from logs.admin_notify import notify_admin

router = Router()  # собственный router для модуля

@router.callback_query(F.data == "add_new_servers")
async def add_new_servers(callback: CallbackQuery):
    if callback.from_user.id not in admins:
        await callback.answer(text="❌ У вас нет доступа к этой функции.", show_alert=True)
        return

    await callback.answer("⏳ Проверка и добавление новых серверов...")
    try:
        added_servers = await sync_servers_to_db()
        if added_servers:
            text = "✅ Добавлены новые серверы:\n" + "\n".join(added_servers)
        else:
            text = "ℹ️ Новых серверов для добавления не найдено."
        await callback.message.edit_text(text)
        logger.info(f"[add_new_servers_callback] Пользователь {callback.from_user.id} синхронизировал серверы: {added_servers}")
    except Exception as e:
        logger.error(f"[add_new_servers_callback] Ошибка при добавлении серверов: {e}")
        await notify_admin(f"Ошибка при добавлении серверов: {e}")
        await callback.message.edit_text("❌ Произошла ошибка при добавлении серверов. Админ уведомлён.")
