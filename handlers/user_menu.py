from aiogram import types, Router, F
from aiogram.types import Message, BotCommand, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.filters.state import StateFilter
from aiogram.fsm.context import FSMContext

from os import path
from data.loader import bot

from database.functions_db_async import *

from datetime import datetime

from keyboard.user_keyboard import *

from handlers.states import SubscriptionState



router = Router()


# Устанавливаем команды для бота
commands = [
    BotCommand(command="/start", description="🏠 Главное меню"),
    BotCommand(command="/tariffs", description="📊 Тарифы"),
    BotCommand(command="/pay", description="💳 Оплатить подписку"),
    BotCommand(command="/my_id", description="🆔 Профиля"),
    BotCommand(command="/support", description="🆘 Помощь"),
]

async def set_commands():
    await bot.set_my_commands(commands=commands)


# ______________________________________________________________________________________________________
@router.message(Command("pay"))
async def pay_sub(msg: Message, state: FSMContext):
    await buy_subscription(msg, state)


@router.message(Command("support"))
async def helping(msg: Message):
    await help_section(msg)


@router.message(Command("my_id"))
async def show_my_id(msg: Message):
    telegram_id = msg.from_user.id
    await msg.answer(text=f"🆔 Профиля: {telegram_id}")


@router.message(Command("tariffs"))
async def show_tariffs(message: types.Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💸 Оплатить тариф", callback_data="pay_subscribe")],
        ]
    )

    text = (
        f"<b>📊 Тарифы:</b>\n\n"
        f"🟢 <b>1 месяц</b> — "
        f"{tariffs_data['month']['1_devices']['price']}₽ / "
        f"{tariffs_data['month']['2_devices']['price']}₽ / "
        f"{tariffs_data['month']['3_devices']['price']}₽ / "
        f"{tariffs_data['month']['5_devices']['price']}₽\n"
        "(1 / 2 / 3 / 5 устройств)\n\n"

        f"🔵 <b>3 месяца</b> — "
        f"{tariffs_data['three_months']['1_devices']['price']}₽ / "
        f"{tariffs_data['three_months']['2_devices']['price']}₽ / "
        f"{tariffs_data['three_months']['3_devices']['price']}₽ / "
        f"{tariffs_data['three_months']['5_devices']['price']}₽\n"
        "(1 / 2 / 3 / 5 устройств)\n\n"

        f"🟠 <b>6 месяцев</b> — "
        f"{tariffs_data['six_months']['1_devices']['price']}₽ / "
        f"{tariffs_data['six_months']['2_devices']['price']}₽ / "
        f"{tariffs_data['six_months']['3_devices']['price']}₽ / "
        f"{tariffs_data['six_months']['5_devices']['price']}₽\n"
        "(1 / 2 / 3 / 5 устройств)\n\n"

        f"🔴 <b>12 месяцев</b> — "
        f"{tariffs_data['year']['1_devices']['price']}₽ / "
        f"{tariffs_data['year']['2_devices']['price']}₽ / "
        f"{tariffs_data['year']['3_devices']['price']}₽ / "
        f"{tariffs_data['year']['5_devices']['price']}₽\n"
        "(1 / 2 / 3 / 5 устройств)\n\n"

        "<b>🎁 Получайте скидки от 7% до 25% — чем больше выбираете, тем выгоднее!</b>"
    )
    await message.answer(text=text, reply_markup=keyboard, parse_mode='HTML')


@router.callback_query(F.data == "show_tariffs")
async def callback_show_tariffs(callback: types.CallbackQuery):
    await show_tariffs(callback.message)
    await callback.answer()



@router.callback_query(F.data == "pay_subscribe")
async def transition_to_payment(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception as e:
        logger.info(f"Не удалось удалить кнопку с оплатой под тарифами: {e}")

    await handle_buy_subscription(callback.from_user.id, callback.message, state)



# Запуск бота
@router.message(Command('start'))
async def start_func(msg: Message):
    telegram_id = msg.from_user.id

    # Проверка регистрации пользователя
    if not await check_user_registered(telegram_id):
        await register_user(telegram_id)
        print(f"Пользователь с telegram_id {telegram_id} зарегистрирован.")

        keyboard_show_tariffs = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🗂️ Выбрать тариф", callback_data="show_tariffs"), (InlineKeyboardButton(text="🎁 Тестовый период", callback_data="trial"))]])

        await msg.answer_photo(
            photo=types.FSInputFile(path.join('images', 'logo.jpg')),
            caption=(
                '🎉 Добро пожаловать в *MVPNet*🌐✨\n\n'
                'Наш сервер \\- не просто сервер\\. Это умная консультация по вашей мобильной технике\\! *Получите ответ на ваш вопрос* в развёрнутом виде в любое время суток\\!\n\n'
                '> 💰💰За 199 рублей в месяц вы получаете умную консультацию в любой момент времени, если у вас что\\-то случилось, мы поможем и объясним, почему ваш телефон работает не корректно\\!\n\n'
                'Благодаря приложению мы сможем идентифицировать проблемы на вашем устройстве\\! *Не забудьте его установить*\\!\n\n'
            ), parse_mode="MarkdownV2",
            reply_markup=keyboard_show_tariffs
        )
    else:
        # Если пользователь уже зарегистрирован, вызвать функцию remaining_days
        await remaining_days(msg)
        keyboard = await main_menu_keyboard()
        await msg.answer(text="Выберите действие в меню: 👇🏼", reply_markup=keyboard)



# ______________________________________________________________________________________________________


# Обработчик кнопки "Остаток дней"
@router.message(F.text == "📆Остаток дней")
async def remaining_days(msg: Message):
    name_client = msg.from_user.first_name
    telegram_id = msg.from_user.id

    deleted_at = await check_date_subscribe(telegram_id)
    limit_ip = await get_limit_device(telegram_id)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💸 Оплатить тариф", callback_data="pay_subscribe")],
        ]
    )


    if deleted_at is None:
        await msg.answer(text=f'👤 <b>Профиль:</b> {name_client}\n'
                              f'____________________\n\n\n'
                              f'❌ У вас нет активной подписки.', parse_mode='HTML', reply_markup=keyboard)


    else:
        try:
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="💳Продлить подписку", callback_data="pay_subscribe")]
                ]
            )

            now = datetime.now()
            formatted_date = deleted_at.strftime('%d.%m.%Y, %H:%M:%S')

            if deleted_at < now:
                # Срок подписки прошёл
                await msg.answer(
                    text=f'👤 Профиль: <b>{name_client}</b>\n'
                    f'____________________\n\n'
                    f'❌ Подписка истекла: <b>{formatted_date}</b> Мск.',
                    parse_mode='HTML', reply_markup=keyboard
                )
            else:
                # Подписка ещё активна
                active_status = '✅'
                delta = deleted_at - now
                days_left = delta.days
                hours_left = delta.seconds // 3600
                minutes_left = delta.seconds % 3600 // 60
                await msg.answer(
                    text=f'👤 Профиль: <b>{name_client}</b>\n'
                    f'____________________\n\n'
                    f'💡Active: {active_status}\n'
                    f'📱Кол-во устройств: {limit_ip}\n'
                    f'⏳ Осталось: <b>| {days_left} дн. | {hours_left} ч. | {minutes_left} м. |</b>\n'
                    f'📅Подписка до: <b>{formatted_date} МСК</b>', parse_mode='HTML'
                )


        except Exception as e:
            print(f"Ошибка при отправке сообщения: {e}")
            await msg.answer("Произошла ошибка при обработке запроса.")



        @router.callback_query(F.data == "extend_the_subscription")
        async def from_profile_to_subscription(callback: CallbackQuery, state: FSMContext):
            await callback.answer()
            await callback.message.delete()
            await buy_subscription(callback.message, state)

# ______________________________________________________________________________________________________


# Обработчик кнопки "Инструкция и ключ"
@router.message(F.text == "⚙️ Инструкция и 🔑 Ключ")
async def instruction_key(msg: Message, state: FSMContext):
    telegram_id = msg.from_user.id
    await state.clear()
    deleted_at = await check_date_subscribe(telegram_id)  # Получаем дату окончания подписки

    if deleted_at is None:
        await msg.answer(text="⚠️ У вас нет активной подписки.")
        return

    now = datetime.now()
    if deleted_at < now:
        formatted_date = deleted_at.strftime('%d.%m.%Y, %H:%M:%S')
        await msg.answer(text=f"❌ Подписка истекла: <b>{formatted_date}</b> Мск.", parse_mode='HTML')
        return

    # Если подписка активна
    active_key = await get_key(telegram_id=telegram_id)
    if active_key is None:
        await msg.answer(text="⚠️ У вас нет активной подписки.")
    else:
        await msg.answer(text="🔑Ключ: 👇🏻")
        await msg.answer(text=f"<pre>{active_key}</pre>", parse_mode="HTML")
        await msg.answer(text="📌 Выберите устройство, на которое планируете установить ключ:", reply_markup=await choosing_a_device())
        await msg.answer(text=f"⚠️<b>Не делитесь ключом.</b> При использовании на устройствах сверх лимита подписки он автоматически блокируется системой!\n", parse_mode='HTML')



# ______________________________________________________________________________________________________

# Обработчик кнопки "💸 Оплатить подписку"
# @router.message(F.text == "💸 Оплатить подписку")
# async def buy_subscription(msg: Message, state: FSMContext):


@router.message(F.text == "💸 Оплатить подписку")
async def buy_subscription(msg: Message, state: FSMContext):
    await handle_buy_subscription(msg.from_user.id, msg, state)
    return


async def handle_buy_subscription(user_id: int, msg: Message, state: FSMContext):

    await state.clear()
    status, subscription = await get_user_subscription_status(user_id)

    if status == 'no_subscription':
        await msg.answer(
            text="<b>❌ У вас нет активной подписки.</b>\n\n"
                 "📅 Выберите срок подписки:",
            reply_markup=await inline_price(),
            parse_mode='HTML'
        )
        await state.set_state(SubscriptionState.no_sub_choose_tariff)

    elif status == 'expired':
        await msg.answer(text="<b>❌ Ваша подписка истекла.</b>\n\n"
                              "📅 <b>Выберите срок продления подписки:</b>",
            reply_markup=await inline_price(),
            parse_mode='HTML'
        )
        await state.set_state(SubscriptionState.expired_choose_tariff)


    elif status == 'active':
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Продлить подписку", callback_data="active_extend"),
            ],
            [
                InlineKeyboardButton(text="⚙️ Изменить кол-во устройств", callback_data="active_change_devices"),
            ]
        ])

        await msg.answer(
            text="<b>✅ У вас уже есть активная подписка.</b>\n\n"
                 "🔄 Продлить подписку: <pre>продление срока подписки с уже установленным количеством устройств в вашей подписке.</pre>\n\n"
                 "⚙️ Изменить количество устройств: <pre>смена количества устройств без продления срока подписки,"
                 "при увеличении количества устройств производится доплата за оставшиеся дни подписки.</pre>\n\n"
                 "<b><u>Что вы хотите сделать?</u></b>",
            reply_markup=keyboard,
            parse_mode='HTML'
        )
        await state.set_state(SubscriptionState.active_choose_action)


# ______________________________________________________________________________________________________

#
# # Обработчик кнопки "Реферальная система"
# @router.message(F.text == "🤝 Реферальная система")
# async def referral_system(msg: Message):
#     await msg.answer("📢 Раздел в разработке.")


# ______________________________________________________________________________________________________


# Обработчик кнопки "Сменить сервер"
@router.message(F.text == "🌍Сменить сервер")
async def change_server(msg: Message, state: FSMContext):
    telegram_id = msg.from_user.id
    await state.clear()
    status, _ = await get_user_subscription_status(telegram_id=telegram_id)

    if status in ('no_subscription', 'expired'):
        await msg.answer(text="🚫 Данный раздел доступен только пользователям с активной подпиской.")
        return

    await msg.answer(
        text="<b>💡 Внимание!</b>\n\n"
             "<pre>Смена сервера подразумевает удаление вашей текущей конфигурации и выдачи новой, соответствующей стране, которую вы выберете.</pre>\n\n"
             "🔄После получения новой конфигурации <b>необходимо удалить старую и по инструкции установить новую.</b>\n"
             "⚙️Инструкцию можете найти в главном меню.\n\n"
             "<b><u>Выберите страну:</u></b>",
        reply_markup=await inline_server_change(),
        parse_mode='HTML'
    )


# ______________________________________________________________________________________________________


# Обработчик кнопки "Промокод"
# @router.message(F.text == "🎁 Промокод")
# async def promo_code(msg: Message):
#     await msg.answer("🎁 Раздел в разработке.")


# ______________________________________________________________________________________________________


# Обработчик кнопки "Помощь"
@router.message(F.text == "🆘 Помощь")
async def help_section(msg: Message):
    await msg.answer(
        "📌 В этом разделе вы найдёте ключевые решения для самых распространённых проблем, связанных с использованием программы.\n\n"
        "В случае, если вы не нашли подходящего решения в предложенном списке, рекомендуем ознакомиться с нашими общими рекомендациями и советами 🔍.\n\n"
        "Если же и после этого у вас остаются вопросы или проблемы, не стесняйтесь обращаться в нашу службу поддержки - мы всегда рады помочь! 💬👍\n\n"
        "Вы всегда можете написать нам с Вашим вопросом: (Аккаунт для поддержки)"
    )


# ______________________________________________________________________________________________________