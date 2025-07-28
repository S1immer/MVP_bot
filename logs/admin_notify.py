from data.louder import bot
from data.config import admins



async def notify_admin(text: str):
    if isinstance(admins, (list, tuple)):
        for admin_id in admins:
            await bot.send_message(chat_id=admin_id, text=text)
    else:
        await bot.send_message(chat_id=admins, text=text)