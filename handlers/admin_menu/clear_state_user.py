from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.base import StorageKey
from data.loader import storage

router = Router()

class ClearStateFSM(StatesGroup):
    waiting_for_user_id = State()

async def clear_user_state(bot: Bot, telegram_id: int):
    key = StorageKey(bot_id=bot.id, user_id=telegram_id, chat_id=telegram_id)
    state = FSMContext(storage=storage, key=key)
    await state.clear()

    try:
        await bot.send_message(telegram_id, text="Ваше состояние было очищено администратором.")
    except Exception as e:
        print(f"Не удалось отправить сообщение пользователю {telegram_id}: {e}")

@router.callback_query(F.data == "clear_state")
async def ask_user_id(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ClearStateFSM.waiting_for_user_id)
    await callback.message.answer("Введите Telegram ID пользователя для очистки state:")
    await callback.answer()

@router.message(ClearStateFSM.waiting_for_user_id)
async def process_user_id(message: Message, state: FSMContext):
    try:
        user_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ ID должен быть числом. Попробуйте ещё раз.")
        return

    await clear_user_state(bot=message.bot, telegram_id=user_id)
    await message.answer(text=f"✅ Состояние пользователя с ID `{user_id}` очищено.", parse_mode="Markdown")
    await state.clear()
