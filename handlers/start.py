from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, ReplyKeyboardRemove
from config import SALON_NAME, SALON_PHONE

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        f"👋 Добро пожаловать в {SALON_NAME}!\n\n"
        f"Я Айя, ваш AI-администратор. Работаю 24/7.\n\n"
        f"Нажмите кнопку меню (≡) слева внизу, чтобы записаться или задать вопрос прямо здесь.",
        reply_markup=ReplyKeyboardRemove()
    )

@router.message(Command("contacts"))
async def contacts(message: Message):
    await message.answer(
        f"📞 Телефон: {SALON_PHONE}\n"
        f"🕘 Работаем: 09:00 — 19:00\n"
        f"📍 г. Бишкек"
    )
