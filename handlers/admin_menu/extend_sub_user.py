from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from data.config import admins
from database.functions_db_async import get_data_for_delet_client
from api_3xui.Update_time_key import extend_time_key
from logs.logging_config import logger
from logs.admin_notify import notify_admin
from datetime import datetime, timedelta
from data.loader import bot

router = Router()

class ExtendSubscriptionFSM(StatesGroup):
    waiting_for_days = State()
    waiting_for_user_id = State()
    waiting_for_confirmation = State()

@router.callback_query(F.data == "admin_extend_sub")
async def start_extend_subscription(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in admins:
        await callback.answer(text="❌ У вас нет доступа к этой функции.", show_alert=True)
        return
    
    await state.set_state(ExtendSubscriptionFSM.waiting_for_days)
    await callback.message.answer("📅 Продление подписки\n\nВведите количество дней для продления:")
    await callback.answer()

@router.message(ExtendSubscriptionFSM.waiting_for_days)
async def process_days_for_extend(message: Message, state: FSMContext):
    if message.from_user.id not in admins:
        return
    
    try:
        days = int(message.text.strip())
        if days <= 0:
            await message.answer("❌ Количество дней должно быть положительным числом. Попробуйте ещё раз:")
            return
        if days > 365:
            await message.answer("❌ Максимальное количество дней - 365. Попробуйте ещё раз:")
            return
    except ValueError:
        await message.answer("❌ Количество дней должно быть числом. Попробуйте ещё раз:")
        return
    
    # Сохраняем количество дней в состоянии
    await state.update_data(extension_days=days)
    await state.set_state(ExtendSubscriptionFSM.waiting_for_user_id)
    
    await message.answer(
        text=f"✅ Количество дней: `{days}`\n\n"
        f"Теперь введите Telegram ID пользователя для продления подписки:",
        parse_mode="Markdown"
    )

@router.message(ExtendSubscriptionFSM.waiting_for_user_id)
async def process_user_id_for_extend(message: Message, state: FSMContext):
    if message.from_user.id not in admins:
        return
    
    try:
        user_id = int(message.text.strip())
        if user_id <= 0:
            await message.answer("❌ ID должен быть положительным числом. Попробуйте ещё раз:")
            return
    except ValueError:
        await message.answer("❌ ID должен быть числом. Попробуйте ещё раз:")
        return
    
    # Получаем количество дней из состояния
    data = await state.get_data()
    extension_days = data['extension_days']
    
    # Проверяем, существует ли пользователь и есть ли у него активная подписка
    user_data = await get_user_data_for_extend(user_id)
    if not user_data:
        await message.answer(
            f"❌ Пользователь с ID `{user_id}` не найден или у него нет активной подписки.\n"
            "Проверьте ID и попробуйте ещё раз:"
        )
        return
    
    server_id, client_uuid, ip_limit = user_data
    
    # Сохраняем данные пользователя в состоянии для подтверждения
    await state.update_data(
        target_user_id=user_id,
        server_id=server_id,
        client_uuid=client_uuid,
        ip_limit=ip_limit
    )
    
    # Показываем сводку и запрашиваем подтверждение
    summary_text = (
        f"📋 Сводка продления подписки:\n\n"
        f"👤 Пользователь: `{user_id}`\n"
        f"🖥️ Сервер: `{server_id}`\n"
        f"📱 Устройств: `{ip_limit}`\n"
        f"📅 Продление на: `{extension_days}` дней\n\n"
        f"Подтверждаете продление подписки?"
    )
    
    # Создаем клавиатуру для подтверждения
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, продлить", callback_data="confirm_extend")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_extend")]
    ])
    
    await message.answer(summary_text, reply_markup=keyboard, parse_mode="Markdown")
    await state.set_state(ExtendSubscriptionFSM.waiting_for_confirmation)

@router.callback_query(F.data == "confirm_extend")
async def confirm_extend_subscription(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in admins:
        await callback.answer(text="❌ У вас нет доступа к этой функции.", show_alert=True)
        return
    
    # Получаем данные из состояния
    data = await state.get_data()
    user_id = data['target_user_id']
    server_id = data['server_id']
    client_uuid = data['client_uuid']
    ip_limit = data['ip_limit']
    extension_days = data['extension_days']
    
    # Дополнительная проверка client_uuid
    if not client_uuid or client_uuid.strip() == "":
        await callback.message.edit_text(
            f"❌ Ошибка: пустой client_uuid для пользователя {user_id}.\n"
            f"Проверьте данные в базе данных."
        )
        logger.error(f"[extend_subscription] Пустой client_uuid для пользователя {user_id}")
        await state.clear()
        return


    # Показываем процесс продления
    status_msg = await callback.message.edit_text("⏳ Продление подписки...")
    
    try:
        # Получаем текущую дату окончания подписки из БД
        from database.functions_db_async import get_date_user
        
        current_subscription_data = await get_date_user(user_id)
        if not current_subscription_data:
            await status_msg.edit_text(
                f"❌ Не удалось получить данные о текущей подписке пользователя {user_id}.\n"
                f"Проверьте, есть ли активная подписка в базе данных."
            )
            logger.error(f"[extend_subscription] Не удалось получить данные подписки для пользователя {user_id}")
            await state.clear()
            return
        
        created_at, deleted_at = current_subscription_data
        
        if not deleted_at:
            await status_msg.edit_text(
                f"❌ У пользователя {user_id} нет активной подписки или дата окончания не установлена."
            )
            logger.error(f"[extend_subscription] Нет даты окончания подписки для пользователя {user_id}")
            await state.clear()
            return
        
        # Вычисляем оставшиеся дни
        current_time = datetime.now()
        remaining_days = (deleted_at - current_time).days
        
        if remaining_days < 0:
            # Подписка уже истекла, начинаем с текущего времени
            new_expiry_time = current_time + timedelta(days=extension_days)
            logger.info(f"[extend_subscription] Подписка истекла, начинаем с текущего времени")
        else:
            # Подписка активна, добавляем к оставшимся дням
            new_expiry_time = deleted_at + timedelta(days=extension_days)
            logger.info(f"[extend_subscription] Оставшиеся дни: {remaining_days}, добавляем {extension_days} дней")
        
        # Конвертируем в UNIX timestamp в миллисекундах
        expiry_timestamp = int(new_expiry_time.timestamp() * 1000)
        
        # Продлеваем подписку на сервере
        extend_result = await extend_time_key(
            telegram_id=user_id,
            server_id_name=server_id,
            client_uuid=client_uuid,
            limit_ip=ip_limit + 1,  # +1 чтобы не было блокировки
            expiry_time=expiry_timestamp
        )
        
        if extend_result:
            # Обновляем дату в базе данных
            from database.functions_db_async import update_subscription_expiry_time
            
            update_result = await update_subscription_expiry_time(user_id, new_expiry_time)
            
            if update_result:
                if remaining_days >= 0:
                    success_text = (
                        f"✅ Подписка успешно продлена!\n\n"
                        f"👤 Пользователь: `{user_id}`\n"
                        f"📅 Продлено на: `{extension_days}` дней\n"
                        f"⏰ Оставшиеся дни: `{remaining_days}` дней\n"
                        f"🕐 Новое окончание: `{new_expiry_time.strftime('%d.%m.%Y %H:%M')}`\n"
                        f"🖥️ Сервер: `{server_id}`\n"
                        f"📱 Устройств: `{ip_limit}`\n\n"
                        f"💾 База данных обновлена"
                    )
                else:
                    success_text = (
                        f"✅ Подписка успешно продлена!\n\n"
                        f"👤 Пользователь: `{user_id}`\n"
                        f"📅 Продлено на: `{extension_days}` дней\n"
                        f"⚠️ Предыдущая подписка была истекшей\n"
                        f"🕐 Новое окончание: `{new_expiry_time.strftime('%d.%m.%Y %H:%M')}`\n"
                        f"🖥️ Сервер: `{server_id}`\n"
                        f"📱 Устройств: `{ip_limit}`\n\n"
                        f"💾 База данных обновлена"
                    )
                
                await status_msg.edit_text(success_text, parse_mode="Markdown")
                logger.info(f"[extend_subscription] Админ {callback.from_user.id} продлил подписку пользователю {user_id} на {extension_days} дней")
                await notify_admin(f"✅ Админ {callback.from_user.id} продлил подписку пользователю {user_id} на {extension_days} дней")
                try:
                    user_message = (
                        f"🎉 Ваша подписка была продлена администратором!\n\n"
                        f"📅 Продлено на: {extension_days} дней\n"
                        f"🕐 Новое окончание подписки: {new_expiry_time.strftime('%d.%m.%Y %H:%M')}\n"
                        f"📱 Количество устройств: {ip_limit}\n\n"
                        f"✨ Спасибо, что пользуетесь нашим сервисом! ✨"
                    )
                    await bot.send_message(chat_id=user_id, text=user_message)
                    logger.info(f"[extend_subscription] Уведомление отправлено пользователю {user_id}")

                except Exception as e:
                    logger.error(f"[extend_subscription] Не удалось отправить уведомление пользователю {user_id}: {e}")
                
            else:
                # Продление на сервере прошло успешно, но обновление БД не удалось
                warning_text = (
                    f"⚠️ Подписка продлена на сервере, но не удалось обновить базу данных!\n\n"
                    f"👤 Пользователь: `{user_id}`\n"
                    f"📅 Продлено на: `{extension_days}` дней\n"
                    f"🕐 Новое окончание: `{new_expiry_time.strftime('%d.%m.%Y %H:%M')}`\n"
                    f"🖥️ Сервер: `{server_id}`\n"
                    f"📱 Устройств: `{ip_limit}`\n\n"
                    f"❌ Обратитесь к администратору для проверки БД"
                )
                
                await status_msg.edit_text(warning_text, parse_mode="Markdown")
                logger.warning(f"[extend_subscription] Подписка продлена на сервере, но БД не обновлена для пользователя {user_id}")
                await notify_admin(f"⚠️ Подписка продлена на сервере, но БД не обновлена для пользователя {user_id}")
        else:
            error_text = f"❌ Не удалось продлить подписку пользователю `{user_id}` на сервере."
            await status_msg.edit_text(error_text, parse_mode="Markdown")
            logger.error(f"[extend_subscription] Админ {callback.from_user.id} не смог продлить подписку пользователю {user_id}")
            await notify_admin(f"❌ Админ {callback.from_user.id} не смог продлить подписку пользователю {user_id}")
    
    except Exception as e:
        error_text = f"❌ Произошла ошибка при продлении подписки: {e}"
        await status_msg.edit_text(error_text)
        logger.error(f"[extend_subscription] Ошибка при продлении подписки пользователю {user_id}: {e}")
        await notify_admin(f"❌ Ошибка при продлении подписки пользователю {user_id}: {e}")
    
    finally:
        await state.clear()

@router.callback_query(F.data == "cancel_extend")
async def cancel_extend_subscription(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in admins:
        await callback.answer(text="❌ У вас нет доступа к этой функции.", show_alert=True)
        return
    
    await callback.message.edit_text("❌ Продление подписки отменено.")
    await state.clear()

async def get_user_data_for_extend(telegram_id: int):
    """
    Получает данные пользователя для продления подписки
    Возвращает (server_id, client_uuid, ip_limit) или None
    """
    try:
        user_data = await get_data_for_delet_client(telegram_id)
        if user_data:
            server_id, client_uuid, ip_limit = user_data
            return server_id, client_uuid, ip_limit
        return None
    except Exception as e:
        logger.error(f"[get_user_data_for_extend] Ошибка получения данных пользователя {telegram_id}: {e}")
        return None
