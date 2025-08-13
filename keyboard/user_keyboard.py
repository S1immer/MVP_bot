import asyncio
import uuid

from api_3xui.Update_time_key import extend_time_key
from api_3xui.authorize import login_with_credentials, link, get_clients
from api_3xui.client import delete_client, add_user
from data.loader import Bot

from aiogram import Router, F
from aiogram.types import KeyboardButton, InlineKeyboardButton, ReplyKeyboardMarkup, InlineKeyboardMarkup, CallbackQuery
from aiogram.fsm.context import FSMContext

from api_3xui.tariff_key_generator import key_generation
from api_3xui.trial_key import create_trial_key

from handlers.states import SubscriptionState

from payment.yookassa.yookassa_function import  create_payment, check_payment_status

from data_servers.tariffs import tariffs_data

from database.functions_db_async import *

from datetime import datetime, timedelta




router = Router()



# -----------------------------------
# 🔹 ФУНКЦИИ СОЗДАНИЯ КЛАВИАТУР
# -----------------------------------


async def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Создает основное меню (ReplyKeyboard)."""
    keyboard_layout = [
        [KeyboardButton(text='📆Остаток дней'), KeyboardButton(text='⚙️ Инструкция и 🔑 Ключ')],
        [KeyboardButton(text='💸 Оплатить подписку'), KeyboardButton(text='🌍Сменить сервер')],
        #KeyboardButton(text='🤝 Реферальная система')], #KeyboardButton(text='🎁 Промокод')],
        [KeyboardButton(text='🆘 Помощь')],
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard_layout, resize_keyboard=True)


async def trial_button() -> InlineKeyboardMarkup:
    """Создает инлайн-кнопку для тестового периода."""
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text='🎁 Тестовый период', callback_data='trial')]]
    )


async def inline_server_change() -> InlineKeyboardMarkup:
    """Создает инлайн-кнопки выбора сервера."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🇩🇪Германия", callback_data='serverchange_germany')],
            [InlineKeyboardButton(text="🇳🇱Нидерланды", callback_data='serverchange_netherlands')]
        ]
    )


async def choice_of_payment_system() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💳 ЮКасса", callback_data='pay_yookassa')],
            [InlineKeyboardButton(text="⭐ Telegram Stars", callback_data='pay_telegram_stars')]
        ]
    )


async def inline_price() -> InlineKeyboardMarkup:
    """Создает инлайн-кнопки с тарифами."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text='🔥 1 месяц', callback_data='month')],
            [InlineKeyboardButton(text='🔥 3 месяца', callback_data='three_months')],
            [InlineKeyboardButton(text='🔥 6 месяцев', callback_data='six_months')],
            [InlineKeyboardButton(text='🔥 12 месяцев', callback_data='year')],
        ]
    )


async def inline_device() -> InlineKeyboardMarkup:
    """Создает инлайн-кнопки с кол-ом устройств"""
    return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text='🔥1 устройство', callback_data='1_devices')],
                [InlineKeyboardButton(text='🔥2 устройства', callback_data='2_devices')],
                [InlineKeyboardButton(text='🔥3 устройства', callback_data='3_devices')],
                [InlineKeyboardButton(text='🔥5 устройств', callback_data='5_devices')]
            ]
        )


async def inline_check_payment(payment_id: str) -> InlineKeyboardMarkup:
    """Создает инлайн-кнопку для проверки платежа."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text='🔄 Проверить оплату', callback_data=f'check_payment_{payment_id}')]
        ]
    )


async def choosing_a_device() -> InlineKeyboardMarkup:
    """Выбор устройства для настройки приложения"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text='🍏iPhone', callback_data='iphone')],
            [InlineKeyboardButton(text='🤖Android', callback_data='android')],
            [InlineKeyboardButton(text='🖥Windows', callback_data='windows')],
            [InlineKeyboardButton(text='💻MacOS', callback_data='macos')]
        ]
    )


# ============================================
# 🔹 Обработчики
# ============================================


async def background_check_payment(bot: Bot, telegram_id: int, payment_id: str, path: str, state: FSMContext, **kwargs):
    """
    Универсальная функция авто-проверки платежа yookassa.,
    path - строка: "no_subscription", "expired", "active"
    kwargs - дополнительные параметры, нужные для логики каждого пути
    """
    for _ in range(120):  # проверяем до 5 минут (10 * 30сек)
        status = await check_payment_status(payment_id)
        if status == "succeeded":
            try:
                if path == "no_subscription":
                    path_for_db = "new_sub"
                    data = await state.get_data()
                    get_period = data.get('tariff')  # например, 'month'
                    get_device = data.get('limit_ip_int')  # например, '1_devices'

                    if not get_period or not get_device:
                        await bot.send_message(telegram_id, text="❌ Не указаны параметры тарифа.")
                        return None

                    if get_period not in tariffs_data or get_device not in tariffs_data[get_period]:
                        await bot.send_message(telegram_id, text="❌ Некорректные параметры тарифа.")
                        return None


                    result = await key_generation(telegram_id, period=get_period, devices=get_device)
                    if result is None:
                        await bot.send_message(telegram_id, text=f"❌ Произошла ошибка при генерации ключа. Напишите в поддержку!\n"
                                                             f"Ваш оплаченный тариф - {get_period} дней, количество устройств:{get_device}.\n"
                                                             f"id платежа: {payment_id}")
                        return None

                    link_data, server_id, tariff_days, device, client_uuid = result

                    await bot.send_message(
                        telegram_id,
                        text=f"✅ Оплата успешно прошла!\n"
                             f"✨ Подписка активирована на {tariff_days} дней, устройств: {device}.\n\n"
                             f"🔑 Ваша конфигурация:\n", parse_mode="HTML"
                    )
                    await bot.send_message(telegram_id, text=f"<pre>{link_data}</pre>", parse_mode="HTML")
                    await bot.send_message(telegram_id, text="📌 Выберите устройство, на которое планируете установить ключ:",
                                           reply_markup=await choosing_a_device())
                    await bot.send_message(telegram_id, text=f"⚠️<b>Не делитесь конфигурацией.</b> При использовании на устройствах сверх лимита подписки "
                             f"она автоматически блокируется системой!\n", parse_mode='HTML')

                    expiry_time_tariff = datetime.now() + timedelta(days=tariff_days)
                    await save_key_to_database(telegram_id=telegram_id,
                                               client_uuid=client_uuid,
                                               active_key=link_data,
                                               ip_limit=device,
                                               server_id=server_id,
                                               expiry_time=expiry_time_tariff
                                               )

                    created_pay = datetime.now()
                    await save_payment_id_to_database(telegram_id, payment_id, created_pay, path_for_db, device, tariff_days)
                    await add_user_db_on_server(device, server_id, telegram_id)


                elif path == "expired":
                    path_for_db = "sub_extension"
                    data = await state.get_data()
                    get_period = data.get('tariff')
                    get_device = data.get('limit_ip_int')

                    user_data_for_extend = await get_user_data_for_extend(telegram_id)
                    if user_data_for_extend:
                        server_id, client_uuid, ip_limit = user_data_for_extend
                    else:
                        await bot.send_message(telegram_id, text=f"[background_check_payment] Ошибка в продлении подписки! Обратитесь в поддержку!")
                        return None

                    tariff_data = tariffs_data[get_period][f"{get_device}_devices"]
                    tariff_days = tariff_data['days']
                    current_time = datetime.now()
                    expiry_time = current_time + timedelta(days=tariff_days)
                    expiry_timestamp = int(expiry_time.timestamp() * 1000)

                    result_extend = await extend_time_key(
                        telegram_id=telegram_id,
                        server_id_name=server_id,
                        client_uuid=client_uuid,
                        limit_ip=ip_limit+1, # +1 чтобы на сервере при смене интернета не заблокировался ключ
                        expiry_time=expiry_timestamp
                    )
                    if result_extend:
                        new_created = datetime.now()
                        new_deleted = new_created + timedelta(tariff_days)
                        await save_the_new_subscription_time_for_extension(telegram_id, new_created, new_deleted)
                        await save_payment_id_to_database(telegram_id, payment_id, new_created, path_for_db, ip_limit, tariff_days)
                        await bot.send_message(telegram_id, text=f"✅ Оплата успешно прошла!\n"
                                                             f"✨ Подписка успешно продлена на {tariff_days} дней!")
                    else:
                        await bot.send_message(telegram_id,
                                               text=f"❌ Не удалось продлить подписку. Обратитесь в поддержку.\n"
                                                    f"Тариф продления - {tariff_days} дней, кол-во устройств: {ip_limit} ")


                elif path == "active":
                    action = kwargs.get("action")  # например "extension" или "change_devices"
                    if action == "active_extend":

                        path_for_db = 'active_extension'
                        data = await state.get_data()
                        get_period = data.get('tariff')
                        get_device = data.get('limit_ip_int')
                        device_limit = f"{get_device}_devices"

                        if not get_period or not device_limit:
                            await bot.send_message(telegram_id,
                                                   text="❌ Не указаны параметры тарифа. Обратитесь в поддержку!")
                            return None

                        if get_period not in tariffs_data or device_limit not in tariffs_data[get_period]:
                            await bot.send_message(telegram_id,
                                                   text="❌ Некорректные параметры тарифа. Обратитесь в поддержку!")
                            return None

                        days = tariffs_data[get_period][device_limit]['days']


                        data_time_sub = await get_date_user(telegram_id)
                        created_at, deleted_at = data_time_sub
                        remaining_days_sub = deleted_at - datetime.now()
                        total_extension = remaining_days_sub + timedelta(days=days)
                        new_deleted = datetime.now() + total_extension


                        user_data_for_extend = await get_user_data_for_extend(telegram_id)
                        if user_data_for_extend:
                            server_id, client_uuid, ip_limit = user_data_for_extend
                        else:
                            await bot.send_message(telegram_id,
                                                   text=f"[background_check_payment] Ошибка в продлении подписки! Обратитесь в поддержку!")
                            return None

                        # Преобразуем дату окончания подписки в timestamp в мс
                        expiry_timestamp = int(new_deleted.timestamp() * 1000)

                        # Отправляем данные на продление
                        result_extend = await extend_time_key(
                            telegram_id=telegram_id,
                            server_id_name=server_id,
                            client_uuid=client_uuid,
                            limit_ip=ip_limit+1, # +1 чтобы на сервере при смене интернета не заблокировался ключ
                            expiry_time=expiry_timestamp
                        )

                        if result_extend:
                            new_created = datetime.now()
                            print(f"new_created - {new_created}")
                            print(f"new_deleted - {new_deleted}")
                            await save_the_new_subscription_time_for_extension(telegram_id, new_created, new_deleted)
                            await save_payment_id_to_database(telegram_id, payment_id, new_created, path_for_db, ip_limit, days)
                            print(f"payment_data - {path_for_db}")
                            await bot.send_message(telegram_id, text=f"✅ Оплата успешно прошла!\n"
                                                                     f"✨ Подписка успешно продлена на {days} дней!")


                    elif action == "active_change_devices":

                        path_for_db = 'active_change_devices'
                        data = await state.get_data()
                        added_devices = data.get('added_devices') # количество устройств (выбранное - существующее) = кол-во устройств для добавления в таблицу с трафиком для серверов
                        get_device = data.get('limit_ip_int')
                        if not get_device:
                            await bot.send_message(telegram_id,
                                                   text="❌ Не удалось получить новое количество устройств.")
                            return None

                        user_data = await get_user_data_for_extend(telegram_id)
                        if not user_data:
                            await bot.send_message(telegram_id, text="❌ Не удалось получить данные пользователя.")
                            return None

                        server_id, client_uuid, ip_limit = user_data

                        subscription = await get_date_user(telegram_id)
                        if not subscription:
                            await bot.send_message(telegram_id, text="❌ Подписка не найдена.")
                            return None

                        _, deleted_at = subscription
                        if not deleted_at:
                            await bot.send_message(telegram_id, text="❌ Не найдена дата окончания подписки.")
                            return None

                        expiry_timestamp = int(deleted_at.timestamp() * 1000)

                        result_extend = await extend_time_key(
                            telegram_id=telegram_id,
                            server_id_name=server_id,
                            client_uuid=client_uuid,
                            limit_ip=get_device + 1,
                            expiry_time=expiry_timestamp
                        )

                        if result_extend:
                            await save_ip_limit(telegram_id, get_device)
                            await add_user_db_on_server(added_devices, server_id, telegram_id)

                            await save_payment_id_to_database(
                                telegram_id=telegram_id,
                                payment_id=payment_id,
                                created_pay=datetime.now(),
                                payment_data=path_for_db,
                                limit_device=get_device,
                                tariff_days=(deleted_at - datetime.now()).days
                            )

                            await bot.send_message(
                                telegram_id,
                                text=f"✅ Количество устройств изменено на {get_device}.\n"
                                     f"📅 Подписка всё так же действует до {deleted_at.date()}."
                            )
                            await state.clear()
                        else:
                            await bot.send_message(telegram_id, text="❌ Не удалось изменить количество устройств.")

                else:
                    # Если путь неизвестен
                    await bot.send_message(telegram_id, text="✅ Оплата подтверждена!")

            except Exception as e:
                print(f"Ошибка при отправке сообщения о подтверждении оплаты: {e}")
            break

        await asyncio.sleep(10)
    else:
        # Если по истечении времени оплаты нет
        try:
            await bot.send_message(
                telegram_id,
                text="⚠️ Оплата не была подтверждена, попробуйте ещё раз."
            )
        except Exception as e:
            print(f"Ошибка при отправке сообщения об ошибке оплаты: {e}")



# ============================================
# 🔹 Обработчики для пути "no_subscription"
# ============================================

# 1. Обработка выбора срока подписки
@router.callback_query(SubscriptionState.no_sub_choose_tariff, F.data.in_(tariffs_data.keys()))
async def no_sub_choose_tariff(callback: CallbackQuery, state: FSMContext):
    print(f"[no_sub_choose_tariff] User: {callback.from_user.id}, tariff chosen: {callback.data}")
    await state.update_data(tariff=callback.data)
    await callback.message.edit_text(
        text="Выберите количество устройств:",
        reply_markup=await inline_device()
    )
    await state.set_state(SubscriptionState.no_sub_choose_devices)


# 2. Обработка выбора количества устройств
@router.callback_query(SubscriptionState.no_sub_choose_devices, F.data.in_(['1_devices', '2_devices', '3_devices', '5_devices']))
async def no_sub_choose_device(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    tariff = data.get("tariff")
    limit_ip_str = callback.data

    print(f"[no_sub_choose_device] User: {callback.from_user.id}, tariff from state: {tariff}, limit_ip_str chosen: {limit_ip_str}")

    tariff_info = tariffs_data[tariff][limit_ip_str]
    days = tariff_info["days"]
    price = tariff_info["price"]
    limit_ip_int = tariff_info["device_limit"]

    print(f"[no_sub_choose_device] Calculated days: {days}, price: {price}, limit_ip_int: {limit_ip_int}")

    await state.update_data(tariff=tariff, limit_ip_int=limit_ip_int, days=days, price=price)

    telegram_id = callback.from_user.id
    confirmation_url, payment_id = await create_payment(
        user_id=telegram_id,
        tariff_date=days,
        price=price,
        quantity_devices=limit_ip_int
    )
    print(f"[choose_device] Payment created with ID: {payment_id}")

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Оплатить", url=confirmation_url)]
        ]
    )

    await callback.message.edit_text(
        text=f"<b>💳 Платеж создан!\n\n💰Сумма: {price}₽\n📱 Устройств: {limit_ip_int}\n📅 Дней: {days}</b>\n\n"
             f"После оплаты нажмите кнопку 'Проверить оплату' или подождите — бот сам проверит через 30 секунд.",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

    await asyncio.create_task(
        background_check_payment(
            bot=callback.bot,
            telegram_id=telegram_id,
            payment_id=payment_id,
            path="no_subscription",
            days=days,
            device_limit=limit_ip_int,
            state=state
        )
    )


# ============================================
# 🔹 Обработчики для пути "expired"
# ============================================
# Обработка выбора срока продления
@router.callback_query(SubscriptionState.expired_choose_tariff, F.data.in_(tariffs_data.keys()))
async def expired_choose_tariff(callback: CallbackQuery, state: FSMContext):
    telegram_id = callback.from_user.id
    # data = await state.get_data()

    # Получаем количество устройств из БД
    limit_ip_int = await get_limit_device(telegram_id)
    if not limit_ip_int:
        await callback.message.answer("❌ Для продления не удалось получить "
                                      "данные (лимит устройств) о вашей подписке.\n"
                                      "Обратитесь в поддержку.")
        return

    tariff = callback.data
    days = tariffs_data[tariff][f"{limit_ip_int}_devices"]["days"]
    price = tariffs_data[tariff][f"{limit_ip_int}_devices"]["price"]
    # device_limit = tariffs_data[tariff][f"{limit_device}_devices"]["device_limit"]

    await state.update_data(tariff=tariff, limit_ip=f"{limit_device}_devices")
    print(tariff, f"{limit_device}_devices")

    confirmation_url, payment_id = await create_payment(
        user_id=telegram_id,
        tariff_date=days,
        price=price,
        quantity_devices=limit_device
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💳Оплатить", url=confirmation_url)]
        ]
    )

    await callback.message.edit_text(
        text=f"<b>💳 Продление подписки создано!\n\n💰Сумма: {price}₽\n📱 Устройств: {limit_device}\n📅 Дней: {days}</b>\n\n"
             f"После оплаты нажмите кнопку 'Проверить оплату' или подождите — бот сам проверит через 30 секунд.",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

    await asyncio.create_task(
        background_check_payment(
            bot=callback.bot,
            telegram_id=telegram_id,
            payment_id=payment_id,
            path="expired",
            days=days,
            device_limit=limit_device,
            state=state
        )
    )


# ============================================
# 🔹 Обработчики для пути "active"
# ============================================

# 1. Обработка выбора действия при активной подписке
@router.callback_query(SubscriptionState.active_choose_action, F.data.in_(["active_extend", "active_change_devices"]))
async def active_choose_action(callback: CallbackQuery, state: FSMContext):
    action = callback.data
    await state.update_data(action=action)

    if action == "active_extend":
        await callback.message.edit_text(
            text="Выберите срок продления подписки:",
            reply_markup=await inline_price()
        )
        await state.set_state(SubscriptionState.active_choose_tariff)

    elif action == "active_change_devices":
        await callback.message.edit_text(
            text="Выберите новое количество устройств:",
            reply_markup=await inline_device()
        )
        await state.set_state(SubscriptionState.active_choose_devices)


# 2. Обработка выбора тарифа продления существующей активной подписки
@router.callback_query(SubscriptionState.active_choose_tariff)
async def active_choose_tariff(callback: CallbackQuery, state: FSMContext):
    telegram_id = callback.from_user.id
    tariff = callback.data  # например: "month", "three_months" и т.д.
    await state.update_data(tariff=tariff)

    data = await state.get_data()
    print("🔧 FSM данные после выбора тарифа:", data)

    tariff_data = tariffs_data.get(tariff)
    if not tariff_data:
        await callback.message.answer("❌ Некорректный тариф.")
        return

    # Получаем текущее количество устройств из базы
    current_limit_device = await get_limit_device(telegram_id)
    price = tariff_data[f'{current_limit_device}_devices']["price"]
    days = tariff_data[f'{current_limit_device}_devices']["days"]
    await state.update_data(limit_ip_int=current_limit_device, days=days, price=price)

    # Создаём платёж
    confirmation_url, payment_id = await create_payment(
        user_id=telegram_id,
        tariff_date=days,
        price=price,
        quantity_devices=current_limit_device
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💳 Оплатить", url=confirmation_url)]
        ]
    )

    await callback.message.edit_text(
        text=(
            f"<b>💳 Продление подписки создано!\n\n"
            f"💰 Сумма: {price}₽\n"
            f"📱 Устройств: {current_limit_device}\n"
            f"📅 Дней: {days}</b>\n\n"
            "После оплаты нажмите кнопку 'Проверить оплату' или подождите — "
            "бот сам проверит через 30 секунд."
        ),
        reply_markup=keyboard,
        parse_mode="HTML"
    )

    await asyncio.create_task(
        background_check_payment(
            bot=callback.bot,
            telegram_id=telegram_id,
            payment_id=payment_id,
            path="active",
            action="active_extend",
            days=days,
            device_limit=current_limit_device,
            state=state
        )
    )


# 3. Обработка выбора нового количества устройств если подписка активная
@router.callback_query(SubscriptionState.active_choose_devices)
async def active_choose_devices(callback: CallbackQuery, state: FSMContext):
    telegram_id = callback.from_user.id
    selected_devices = int(callback.data.split("_")[0])
    current_user_limit_ip = await get_limit_device(telegram_id)

    subscription = await get_date_user(telegram_id)
    if not subscription:
        await callback.message.answer("❌ Подписка не найдена.")
        return

    created_at, deleted_at = subscription

    if not deleted_at:
        await callback.message.answer("❌ Не найдена дата окончания подписки в базе данных.\n"
                                      "Обратитесь в поддержку!")
        return

    if selected_devices == current_user_limit_ip:
        await callback.answer(text="ℹ️ У вас уже выбрано это количество устройств.", show_alert=True)
        return

    if selected_devices < current_user_limit_ip:
        server_id, client_uuid, ip_limit = await get_user_data_for_extend(telegram_id)
        expiry_timestamp = int(deleted_at.timestamp() * 1000)
        # Уменьшаем без оплаты
        await extend_time_key(telegram_id=telegram_id,
                          server_id_name=server_id,
                          client_uuid=client_uuid,
                          limit_ip=selected_devices+1, # +1 чтобы на сервере при смене интернета не заблокировался ключ
                          expiry_time=expiry_timestamp
        )
        dell = current_user_limit_ip - selected_devices
        await delete_user_db_on_server(dell, server_id, telegram_id)
        await save_ip_limit(telegram_id, selected_devices)
        await callback.message.delete()
        await callback.message.answer(
            f"✅ Количество устройств уменьшено с {current_user_limit_ip} до {selected_devices}.\n"
            f"📅 Подписка действует до {deleted_at.date()}."
        )
        await state.clear()
        return

    # Увеличиваем — считаем доплату
    added_devices = selected_devices - current_user_limit_ip
    days_remaining = (deleted_at - datetime.now()).days
    if days_remaining <= 0:
        await callback.message.answer("❌ Срок вашей подписки уже истёк. Продлите её перед изменением.")
        await state.clear()
        return

    price = added_devices * days_remaining * 6

    # Создаём платёж
    confirmation_url, payment_id = await create_payment(
        user_id=telegram_id,
        tariff_date=0,
        price=price,
        quantity_devices=selected_devices
    )
    await state.update_data(limit_ip=selected_devices, payment_id=payment_id, added_devices=added_devices)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="💳 Оплатить", url=confirmation_url)]]
    )

    await callback.message.edit_text(
        text=f"<b>💳 Платёж за изменение количества устройств создан!</b>\n\n"
             f"📱 Было: {current_user_limit_ip} → Будет: {selected_devices}\n"
             f"🕒 Осталось дней подписки: {days_remaining}\n"
             f"➕ Добавляем устройств: {selected_devices - current_user_limit_ip}\n"
             f"🧮 Рассчёт доплаты: {days_remaining} * {selected_devices - current_user_limit_ip} * 6 ₽\n\n"
             f"💰 Доплата: {price}₽\n\n"
             f"❕ Стоимость — 6 ₽ за устройство в день.\n"
             f"❕ Доплата считается только за оставшиеся дни подписки.\n"
             f"❕ Срок подписки не изменяется.",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

    # Фоновая проверка оплаты
    await asyncio.create_task(
        background_check_payment(
            bot=callback.bot,
            telegram_id=telegram_id,
            payment_id=payment_id,
            path="active",
            action="active_change_devices",
            device_limit=selected_devices,
            state=state
        )
    )


# ============================================
# 🔹 Обработчики для смены страны
# ============================================

@router.callback_query(F.data.startswith("serverchange_"))
async def server_change(callback: CallbackQuery):
    """
    Смена сервера
    # 1. Получаем server_id и client_uuid пользователя из БД
    # 2. Ищем доступные сервера по country_code
    # 3. Выбираем сервер (скрипт на выбор нового сервера -> получаем новый server_id)
    # 4. Генерация новой конфигурации (авторизуемся на новый сервер, добавляем клиента с его остаточным сроком подписки и ip_limit)
    # 5. Отправляем конфигурацию (отправляем новый key из бд пользователю)
    # 6. Если новый ключ на новом сервере созданы и ключ отправлен пользователю, удаляем старого пользователя со старого сервера
    # 7. Обновляем данные в базе (server_id, key)
    """
    country_code = callback.data.split("serverchange_")[1]
    telegram_id = callback.from_user.id

    # 1.
    client_data = await get_data_for_delet_client(telegram_id)
    if not client_data:
        await callback.answer(
            text="⚠️ Для выполнения смены сервера не хватает данных в нашей базе.\n"
                 "❗️ Рекомендуем обратиться в поддержку для уточнения информации.",
            show_alert=True
        )
        return None

    old_server_id, old_client_uuid, ip_limit = client_data

    # 2.
    # 3.
    new_server_id = await get_least_loaded_server_by_code(
        name_country=country_code,
        current_server_id=old_server_id
    )
    if new_server_id is None:
        await callback.answer(
            text="⚠️ Нет доступных серверов для смены. Попробуйте другую страну.",
            show_alert=True
        )
        return None

    await callback.message.delete()

    loading_msg = await callback.bot.send_message(
        chat_id=telegram_id,
        text="⏳ Смена сервера..."
    )

    new_session_3x = None
    old_session_3x = None

    try:
        # 4.
        datetime_user = await get_date_user(telegram_id)

        if not datetime_user:
            await loading_msg.delete()
            await callback.answer(
                text="⚠️ Не удалось получить данные о вашей подписке или дата подписки уже истекла.",
                show_alert=False
            )
            return None

        _, deleted_at = datetime_user
        new_session_3x = await login_with_credentials(server_name=new_server_id)

        if not new_session_3x:
            await loading_msg.delete()
            await callback.answer(
                text="⚠️ Не удалось авторизоваться на новом сервере, попробуйте еще раз.\n",
                show_alert=False
            )
            await notify_admin(f"⚠️ При смене сервера не удалось авторизоваться на сервер - {new_server_id}\n"
                               f"⚠️ Нужно проверить работоспособность сервера!")
            return None

        new_client_uuid = str(uuid.uuid4())
        deleted_at_unix_ms = int(deleted_at.timestamp() * 1000)

        await add_user(
            session=new_session_3x,
            server_id_name=new_server_id,
            client_uuid=new_client_uuid,
            telegram_id=str(telegram_id),
            limit_ip=ip_limit,
            total_gb=0,
            expiry_time=deleted_at_unix_ms,
            enable=True,
            flow='xtls-rprx-vision'
        )

        response = await get_clients(new_session_3x, new_server_id)
        if 'obj' not in response or len(response['obj']) == 0:
            await loading_msg.delete()
            await callback.answer(
                text="⚠️ Не удалось получить список клиентов на новом сервере\n"
                     "Обратитесь в поддержку!",
                show_alert=False
            )
            return None

        link_data = await link(new_session_3x, new_server_id, new_client_uuid, str(telegram_id))
        if not link_data:
            await loading_msg.delete()
            await callback.answer(text=f"⚠️ Не удалось выдать конфигурацию подключения, обратитесь в поддержку для ее получения!")
            await notify_admin(text=f"При смене сервера c {old_server_id} на - {new_server_id}"
                                    f"пользователю - {telegram_id} не выдали конфигурацию.")
            return None
        else:
            await save_key_to_database(
                telegram_id=telegram_id,
                client_uuid=new_client_uuid,
                active_key=link_data,
                ip_limit=ip_limit,
                server_id=new_server_id
            )

            await add_user_db_on_server(
                quantity_users=ip_limit,
                server_name=new_server_id,
                telegram_id=telegram_id
            )

        # 5.
        try:
            await callback.bot.send_message(
                chat_id=telegram_id,
                text=f"🔑 Конфигурация:"
            )
            await callback.bot.send_message(
                chat_id=telegram_id,
                text=f"<pre>{link_data}</pre>",
                parse_mode='HTML'
            )
        except Exception as e:
            await loading_msg.delete()
            await notify_admin(text=f"⚠️ Не удалось отправить новую конфигурацию (ключ) пользователю - {telegram_id}, ошибка: {e}")
            await callback.answer(
                text="❌ Не удалось отправить новую конфигурацию для подключения. Смена сервера отменена.",
                show_alert=False
            )
            return None

        # 6. Если отправка успешна — только тогда удаляем старого пользователя

        # 7.
        old_session_3x = await login_with_credentials(server_name=old_server_id)
        if not old_session_3x:
            await notify_admin(text=f"✅ Пользователь успешно получил новую конфигурацию, при смене сервера."
                                    f"⚠️ При смене сервера, пользователь - {telegram_id} не был\n"
                                    f"удален со старого сервера - {old_server_id}\n"
                                    f"⚠️ Нужно удалить в веб-панели пользователя со старого сервера - {old_server_id}\n"
                                    f"⚠️ Количество устройств пользователя на старом сервере - {ip_limit}"
                                    f"⚠️ Удалить его количество устройств в базе данных, таблица traffic_data, столбец quantity_users")
        else:
            await delete_client(
                session=old_session_3x,
                server_id_name=old_server_id,
                client_id=old_client_uuid
            )

            await delete_user_db_on_server(
                quantity_users=ip_limit,
                server_name=old_server_id,
                telegram_id=telegram_id
            )

        await notify_admin(text=f"✅ Пользователь - {telegram_id} "
                                f"успешно сменил сервер с {old_server_id} на {new_server_id}")

    except Exception as e:
        await notify_admin(f"⚠️ Пользователь: {telegram_id}\n"
                           f"⚠️ Старый сервер: {old_server_id}\n"
                           f"⚠️ Новый сервер: {new_server_id}\n"
                           f"⚠️ Ошибка при смене сервера: {e}\n"
                           )
        await callback.answer(
            text="⚠️ Произошла ошибка при смене сервера. Попробуйте еще раз или позже.",
            show_alert=False
        )
        return None

    finally:
        # Удаляем сообщение загрузки в любом случае
        await loading_msg.delete()

        # Закрываем индикатор на кнопке
        await callback.answer()
        if 'new_session_3x' in locals() and new_session_3x:
            await new_session_3x.close()

        if 'old_session_3x' in locals() and old_session_3x:
            await old_session_3x.close()
    return None


# Регистрация обработчика callback-запроса для тестового периода
@router.callback_query(lambda query: query.data == 'trial')
async def trial_button_callback_handler(query: CallbackQuery):
    await trial_button_callback(query)


async def trial_button_callback(query: CallbackQuery):
    telegram_id = query.from_user.id
    server_id_name = None
    try:
        trial_used = await check_used_trial_period(telegram_id=telegram_id)
        if trial_used:
            await query.answer(text="❗Вы уже использовали пробный период.",
                               replay_markup=await main_menu_keyboard(),
                               show_alert=True)
            return None

        sub_status, _ = await get_user_subscription_status(telegram_id=telegram_id)
        if sub_status != "no_subscription":
            await query.answer(text="❗Пробный период доступен только при отсутствии подписки.",
                               reply_markup=await main_menu_keyboard(),
                               show_alert=True)
            return None

        key_data = await create_trial_key(telegram_id)

        if not key_data:
            await query.bot.send_message(
                chat_id=telegram_id,
                text="⚠️ Не удалось сформировать тестовый ключ. Обратитесь в поддержку!",
                reply_markup=await main_menu_keyboard()
            )
            return None

        connect_link, client_uuid, limit_ip, server_id_name, expiry_time = key_data

        await save_key_to_database(telegram_id=telegram_id,
                                    client_uuid=client_uuid,
                                    active_key=connect_link,
                                    ip_limit=limit_ip,
                                    server_id=server_id_name,
                                    expiry_time=expiry_time
                                    )

        await add_user_db_on_server(limit_ip, server_id_name, telegram_id)

        await query.answer(text="⏳Создание ключа...")
        await query.bot.send_message(chat_id=telegram_id, text="🔑Тестовая конфигурация: 👇🏻")

        await query.bot.send_message(chat_id=telegram_id,
                                     text=f"<pre>{connect_link}</pre>",
                                     reply_markup=await main_menu_keyboard(),
                                     parse_mode="HTML")

        await query.bot.send_message(chat_id=telegram_id,
                                     text="Выберите устройство, на которое планируете установить конфигурацию:",
                                     reply_markup=await choosing_a_device()
                                     )

        await add_user_trial_period(telegram_id=telegram_id)


    except Exception as e:
        logger.error(f"Ошибка в trial_button_callback: {e}\n telegram_id: {telegram_id}\n server_id: {server_id_name}")
        await query.bot.send_message(chat_id=telegram_id,
                                     text="⚠️ Ошибка при создании тестового ключа. Обратитесь в поддержку!",
                                     reply_markup=await main_menu_keyboard())



@router.callback_query(F.data.in_(['iphone', 'android', 'windows', 'macos']))
async def show_instruction(callback_query: CallbackQuery):
    try:
        callback_data = callback_query.data
        instruction_texts = {
            'iphone': "Инструкция для 🍏<b>iPhone:</b> \n\n"
                     "<b>1. Скопируйте ключ доступа.</b>\n\n"
                     "<b>2. Установите приложение</b> 🌐<a href='https://apps.apple.com/ru/app/v2box-v2ray-client/id6446814690'>V2Box</a>.\n\n"
                     "<b>3.</b> Откройте <b>V2Box.</b>\n\n"
                     "<b>4.</b> Перейдите снизу в раздел <b>''Configs''</b>, нажмите ''+'' в правом верхнем углу и выберите <b>''Вставить ключ из буфера обмена'' / ''Import v2ray uri from clipboard''.</b>\n\n"
                     "<b>5.</b> В разделе <b>''Configs''</b> кликните на добавленный ключ, а затем перейдите в раздел <b>''Home''</b> и нажмите кнопку подключения.\n\n",

            # 'iphone': "Инструкция для 🍏<b>iPhone:</b> \n\n"
            #         "<b>1. Скопируйте ключ доступа.</b>\n\n"
            #         "<b>2. Установите приложение</b> 🌐<a href='https://apps.apple.com/ru/app/v2raytun/id6476628951'>V2RayTun</a> (можно найти в App Store).\n\n"
            #         "<b>3. Запустите V2RayTun</b> и нажмите на значок ''+'' в правом верхнем углу.\n\n"
            #         "<b>4. Нажмите ''Добавить из буфера''</b> и затем <b>''Разрешить вставку''.</b>\n\n"
            #          "<b>5. Выберите добавленную конфигурацию</b> и нажмите <b>''Подключиться''</b> для начала работы.\n\n",

            'android': "Инструкция для 🤖<b>Android:</b> \n\n" 
                    "<b>1. Скопируйте ключ доступа.</b>\n\n"
                    "<b>2. Установите приложение</b> 🌐<a href='https://play.google.com/store/search?q=hiddifyNG&c=apps'>HiddifyNG</a>.\n\n"
                    "<b>3. Запустите HiddifyNG</b> и нажмите <b>''Import from clipboard''</b>, затем подтвердите.\n\n"
                    "<b>4.</b> Нажмите <b>''Click to connect''</b> и затем <b>''Ok''.</b>\n\n",

            'windows': "Инструкция для 🖥<b>Windows:</b> \n\n"
                    "<b>1. Скопируйте ключ доступа.</b>\n\n"
                    "<b>2.</b> Установите приложение 🌐<a href='https://github.com/hiddify/hiddify-next/releases/download/v2.5.7/Hiddify-Windows-Setup-x64.exe'>Hiddify</a>👈🏻 <b>нажмите для установки приложения.</b>\n\n"
                    "<b>3.</b> Запустите установленный файл Hiddify <b>от имени администратора.</b>\n\n"
                    "<b>4.</b> Нажмите <b>''Новый профиль''</b> для добавления ключа из буфера обмена.\n\n"
                    "<b>5.</b> В правом верхнем углу будут настройки, <b>откройте их</b> и <b>нажмите VPN.</b>\n\n",

            'macos': "Инструкция для 💻<b>MacOS:</b> \n\n"
                    "<b>1. Скопируйте ключ доступа.</b>\n\n"
                    "<b>2. Установите приложение</b> 🌐<a href='https://apps.apple.com/ru/app/v2box-v2ray-client/id6446814690'>V2Box</a>.\n\n"
                    "<b>3.</b> Откройте <b>V2Box.</b>\n\n"
                    "<b>4.</b> Перейдите в раздел <b>''Configs''</b>, нажмите ''+'' в правом верхнем углу и выберите <b>''Вставить ключ из буфера обмена'' / ''Import v2ray uri from clipboard''.</b>\n\n"
                    "<b>5.</b> В разделе <b>''Configs''</b> кликните на добавленный ключ, а затем перейдите в раздел <b>''Home''</b> и нажмите кнопку подключения.\n\n"
        }

        if callback_data in instruction_texts:
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text='🔙 Назад',
                                          callback_data='return_to_instruction_choice')]
                ]
            )
            await callback_query.message.edit_text(
                text=instruction_texts[callback_data],
                parse_mode="HTML",
                disable_web_page_preview=True,
                reply_markup=keyboard
            )
            await callback_query.answer()

    except Exception as e:
        logger.error(f"Ошибка в show_instruction: {e}")
        await callback_query.message.answer("⚠️ Ошибка при загрузке инструкции.")


@router.callback_query(F.data == 'return_to_instruction_choice')
async def return_to_instruction_choice_callback(query: CallbackQuery):
    try:
        keyboard = await choosing_a_device()
        if keyboard is None:
            await query.answer("⚠️ Не удалось загрузить список инструкций. Попробуйте снова.")
            return

        await query.message.edit_text(
            text="📌 Выберите устройство, на которое планируете установить ключ:",
            reply_markup=keyboard
        )
        await query.answer()

    except Exception as e:
        logger.error(f"Ошибка в return_to_instruction_choice_callback: {e}")
        await query.answer("⚠️ Ошибка при возврате к выбору инструкции.")


