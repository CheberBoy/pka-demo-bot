import os
import tempfile
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from utils.ai_client import get_ai_response
from utils.voice_processor import transcribe_audio
from db.database import is_known_user, register_user
from create_bot import bot

router = Router()


async def _process_text(message: Message, state: FSMContext, text: str):
    """Общая логика: отправить текст в AI и ответить."""
    known = await is_known_user(message.from_user.id)
    if not known:
        await register_user(message.from_user.id)

    data = await state.get_data()
    history = data.get("chat_history", [])
    history.append({"role": "user", "content": text})
    if len(history) > 20:
        history = history[-20:]

    await message.chat.do("typing")
    response = await get_ai_response(history, is_new_user=not known)

    history.append({"role": "assistant", "content": response})
    await state.update_data(chat_history=history)
    await message.answer(response)


@router.message(F.voice)
async def handle_voice(message: Message, state: FSMContext):
    """Голосовое сообщение: расшифровать и передать в AI."""
    current_state = await state.get_state()
    if current_state is not None:
        return  # Идёт процесс записи — не перехватывать

    await message.chat.do("typing")

    # Скачиваем .ogg во временный файл
    voice_file = await bot.get_file(message.voice.file_id)
    tmp = tempfile.NamedTemporaryFile(suffix=".ogg", delete=False)
    tmp_path = tmp.name
    tmp.close()

    try:
        await bot.download_file(voice_file.file_path, tmp_path)
        text = transcribe_audio(tmp_path)
    finally:
        os.unlink(tmp_path)

    if text.startswith("["):
        await message.answer("Не смог разобрать голосовое 😔 Попробуйте написать текстом.")
        return

    await message.answer(f"🎤 Вы сказали: _{text}_", parse_mode="Markdown")
    await _process_text(message, state, text)


@router.message(F.text & ~F.text.startswith("/"))
async def handle_free_text(message: Message, state: FSMContext):
    """Перехватывает свободный текст и отправляет в Claude."""
    current_state = await state.get_state()
    if current_state is not None:
        return  # Если идёт процесс записи — не перехватывать

    await _process_text(message, state, message.text)
