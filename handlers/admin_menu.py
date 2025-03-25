from aiogram.filters import Command
from aiogram.types import Message
from data.config import admins
from data.louder import *
from aiogram import Router




router = Router()

def is_admin(msg):
    return msg.from_user.id == admins

@router.message(is_admin, Command('admin'))
async def start_func(msg: Message):
    await msg.answer('hello admin')