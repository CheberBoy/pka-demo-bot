from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from config import SALON_NAME, SALON_PHONE
from keyboards.main_kb import get_main_keyboard

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        f"👋 Добро пожаловать в {SALON_NAME}!\n\n"
        f"Я Айя, ваш AI-администратор. Работаю 24/7.\n\n"
        f"Используйте меню внизу, чтобы записаться или просто спросите меня!",
        reply_markup=get_main_keyboard()
    )

@router.message(Command("contacts"))
async def contacts(message: Message):
    await message.answer(
        f"📞 Телефон: {SALON_PHONE}\n"
        f"🕘 Работаем: 09:00 — 19:00\n"
        f"📍 г. Бишкек"
    )
