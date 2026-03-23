from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from utils.ai_client import get_ai_response
from db.database import is_known_user, register_user

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

    # Проверяем, знакомый ли клиент
    known = await is_known_user(message.from_user.id)
    if not known:
        await register_user(message.from_user.id)

    # Загружаем историю диалога
    data = await state.get_data()
    history = data.get("chat_history", [])

    # Добавляем новое сообщение пользователя
    history.append({"role": "user", "content": message.text})

    # Ограничиваем историю последними 20 сообщениями (10 пар)
    if len(history) > 20:
        history = history[-20:]

    await message.chat.do("typing")
    response = await get_ai_response(history, is_new_user=not known)

    # Добавляем ответ бота в историю
    history.append({"role": "assistant", "content": response})
    await state.update_data(chat_history=history)

    await message.answer(response)
