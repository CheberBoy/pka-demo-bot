"""
Enhanced AI Chat Handler with Database Search Integration
Использует salon_search для ответов из БД, Claude для сложных вопросов
"""

import logging
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from pathlib import Path
import sqlite3

from utils.ai_client import get_ai_response
from db.database import is_known_user, register_user

router = Router()
logger = logging.getLogger(__name__)

# Database path
DB_PATH = Path(__file__).parent.parent / "db" / "salon.db"

from utils.quantum_search_with_rtk import QuantumSearchWithRTK


# Initialize search
db_search = QuantumSearchWithRTK(str(DB_PATH))

@router.message(F.voice)
async def handle_voice(message: types.Message, state: FSMContext):
    """Голосовое сообщение: расшифровать и передать в AI."""
    current_state = await state.get_state()
    if current_state is not None:
        return

    await message.chat.do("typing")

    import os
    import tempfile
    from utils.voice_processor import transcribe_audio
    from create_bot import bot

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
    
    # Store the transcribed text inside the message object and pass it to DB handler
    message.override_text = text
    await handle_message_with_db(message, state)


@router.message()
async def handle_message_with_db(message: types.Message, state: FSMContext):
    """
    Handle message with Quantum Search context injection into Claude
    """
    
    try:
        user_id = message.from_user.id
        user_text = getattr(message, 'override_text', message.text)
        user_text = (user_text or message.caption or "").strip()
        
        if not user_text:
            return
            
        logger.info(f"User {user_id}: {user_text}")
        
        # STEP 1: Smart AI Search using BM25 + Cosine Similarity
        search_results = db_search.search_with_context_limit(user_text, max_tokens=1500)
        
        context_str = ""
        if search_results:
            context_str = "ДАННЫЕ ИЗ БАЗЫ (ОТВЕЧАЙ ОПИРАЯСЬ НА НИХ):\n"
            for r in search_results:
                summary = r.get('summary_short', r.get('summary', ''))
                context_str += f"- {summary}\n"
        
        # STEP 2: Prepend contextual data for Claude to read (but not for chat history token drain)
        known = await is_known_user(user_id)
        if not known:
            await register_user(user_id)

        data = await state.get_data()
        history = data.get("chat_history", [])
        
        if context_str:
            prompt_with_context = f"{context_str}\n\nВОПРОС: {user_text}"
        else:
            prompt_with_context = user_text
            
        history.append({"role": "user", "content": prompt_with_context})
        if len(history) > 20:
            history = history[-20:]

        await message.chat.do("typing")
        answer = await get_ai_response(history, is_new_user=not known)

        # CLEANUP: Remove the large database context string from the last user message so the prompt size doesn't bloat over time
        if history and history[-1]["role"] == "user":
            history[-1]["content"] = user_text
            
        history.append({"role": "assistant", "content": answer})
        await state.update_data(chat_history=history)
        
        await message.answer(answer)
        logger.info(f"Response (quantum_claude): {answer[:50]}...")
    
    except Exception as e:
        logger.error(f"Error: {e}")
        await message.answer("Извините, произошла ошибка. Попробуйте разобраться позже.")
