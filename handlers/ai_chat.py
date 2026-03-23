from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from utils.ai_client import get_ai_response

router = Router()

MENU_BUTTONS = ["📅 Записаться", "💬 Задать вопрос", "📞 Контакты"]

@router.message(F.text == "💬 Задать вопрос")
async def ask_question_prompt(message: Message):
    await message.answer("Задайте ваш вопрос — отвечу в течение нескольких секунд 🤖")

@router.message(F.text & ~F.text.startswith("/"))
async def handle_free_text(message: Message, state: FSMContext):
    """Перехватывает свободный текст и отправляет в Claude"""
    current_state = await state.get_state()
    if current_state is not None:
        return  # Если идёт процесс записи — не перехватывать

    if message.text in MENU_BUTTONS:
        return

    await message.chat.do("typing")
    response = await get_ai_response(message.text)
    await message.answer(response)
