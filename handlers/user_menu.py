from aiogram import F
from aiogram.types import Message, BotCommand
from aiogram.filters import Command
from aiogram import types
from os import path
from keyboard.user_keyboard import *
from data.louder import bot
from database.functions_db import register_user
from aiogram import Router



router = Router()

# Устанавливаем команды для бота
commands = [
    BotCommand(command="/start", description="Запустить бота"),
]

async def set_commands():
    await bot.set_my_commands(commands=commands)

# Запуск бота
@router.message(Command('start'))
async def start_func(msg: Message):
    user_id = msg.from_user.id
    register_user(user_id)
    print(f"Пользователь с ID {user_id} запустил бота.")

    await msg.answer_photo(
        photo=types.FSInputFile(path.join('images', 'logo.jpg')),
        caption=(
            '🎉 Добро пожаловать в *MVPNet*🌐✨\n\n'
            'Наш сервер \\- не просто сервер\\. Это умная консультация по вашей мобильной технике\\! *Получите ответ на ваш вопрос* в развёрнутом виде в любое время суток\\!\n\n'
            '> 💰💰За 199 рублей в месяц вы получаете умную консультацию в любой момент времени, если у вас что\\-то случилось, мы поможем и объясним, почему ваш телефон работает не корректно\\!\n\n'
            'Благодаря приложению мы сможем идентифицировать проблемы на вашем устройстве\\! *Не забудьте его установить*\\!\n\n'
        ), parse_mode="MarkdownV2",
        reply_markup=await trial_button(),
        # Кнопка "Тестовый период"
    )
    await msg.answer (text='Выберите действие в меню:',reply_markup=await main_menu_keyboard())  # Главное меню (ReplyKeyboard)


# Обработчик кнопки "Остаток дней"
@router.message(F.text == "Остаток дней")
async def my_tariff(msg: Message):
    await msg.answer(
        f'👤 Профиль: {msg.from_user.username}\n\n'
        f'<b>-- ID:</b> {msg.from_user.id}\n\n'
        f'<b>Добро пожаловать в ваш личный кабинет! Здесь вы можете:</b>\n'
        f'🚀 Посмотреть свои ключи.\n'
        f'💰 Купить ключ.\n'
        f'🆘 Обратиться в поддержку.\n'
        f'<b>Выберите необходимое действие, и мы поможем вам!</b>'
        )

# Обработчик кнопки "Инструкция и ключ"
@router.message(F.text == "⚙️ Инструкция и 🔑 Ключ")
async def instruction_key(msg: Message):
    await msg.answer(text="⚙️ Раздел в разработке.", reply_markup=await main_menu_keyboard())

# Обработчик кнопки "Оплатить подписку"
@router.message(F.text == "💸 Оплатить подписку")
async def buy_subscription(msg: Message):
    await msg.answer(text="<b>Выберите период вашей подписки:</b>", reply_markup=await inline_price())

# Обработчик кнопки "Реферальная система"
@router.message(F.text == "🤝 Реферальная система")
async def referral_system(msg: Message):
    await msg.answer("📢 Раздел в разработке.")

# Обработчик кнопки "Канал"
@router.message(F.text == "📺 Канал")
async def channel(msg: Message):
    await msg.answer("🔔 Подпишитесь на наш канал: https://t.me/acesstothewords")

# Обработчик кнопки "Промокод"
@router.message(F.text == "🎁 Промокод")
async def promo_code(msg: Message):
    await msg.answer("🎁 Раздел в разработке.")

# Обработчик кнопки "Помощь"
@router.message(F.text == "🆘 Помощь")
async def help_section(msg: Message):
    await msg.answer(
        "📌 В этом разделе вы найдёте ключевые решения для самых распространённых проблем, связанных с использованием программы.\n\n"
        "В случае, если вы не нашли подходящего решения в предложенном списке, рекомендуем ознакомиться с нашими общими рекомендациями и советами 🔍.\n\n"
        "Если же и после этого у вас остаются вопросы или проблемы, не стесняйтесь обращаться в нашу службу поддержки - мы всегда рады помочь! 💬👍\n\n"
        "Вы всегда можете написать нам с Вашим вопросом: (Аккаунт для поддержки)"
    )
