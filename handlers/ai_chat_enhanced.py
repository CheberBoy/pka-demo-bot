"""
Enhanced AI Chat Handler with Quantum Search + RTK Integration
Использует поиск в БД перед Claude для экономии токенов и быстроты
"""

import logging
from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from config import ANTHROPIC_API_KEY
from utils.ai_client import get_ai_response
from utils.quantum_search_with_rtk import QuantumSearchWithRTK
import sqlite3
from pathlib import Path

router = Router()
logger = logging.getLogger(__name__)

# Инициализируем Quantum Search
DB_PATH = Path(__file__).parent.parent / "db" / "salon.db"
search_engine = QuantumSearchWithRTK(str(DB_PATH))

class SearchStats:
    """Собираем статистику поисков"""
    total_searches = 0
    db_answers = 0  # вопросы которые ответили из БД
    claude_calls = 0  # вопросы которые пошли в Claude
    tokens_saved = 0

@router.message()
async def handle_all_messages(message: types.Message, state: FSMContext):
    """
    Main message handler with Quantum Search + Claude fallback
    
    Workflow:
    1. Try to search in database (fast, free)
    2. If confident → answer from DB
    3. If not sure → use Claude (smart, but costs tokens)
    4. Save to conversation history for learning
    """
    
    try:
        user_id = message.from_user.id
        user_text = message.text.strip()
        
        logger.info(f"User {user_id}: {user_text}")
        
        # STEP 1: Попробуем поискать в БД
        search_results = search_engine.search_smart(
            query=user_text,
            limit=3,
            compress=True  # RTK compression
        )
        
        SearchStats.total_searches += 1
        
        # STEP 2: Анализируем результаты поиска
        if search_results and search_results[0]['score'] > 0.75:
            # УВЕРЕНЫ в ответе → отвечаем из БД
            answer = search_results[0]['summary_short']
            source = "db"
            SearchStats.db_answers += 1
            
            logger.info(f"✓ DB Answer (confidence: {search_results[0]['score']:.2%})")
        
        else:
            # НЕ уверены → вызываем Claude
            state_data = await state.get_data()
            messages = state_data.get('messages', [])
            
            # Добавляем текущее сообщение
            messages.append({
                'role': 'user',
                'content': user_text
            })
            
            # Получаем ответ от Claude
            answer = await get_ai_response(messages, is_new_user=len(messages) <= 1)
            source = "claude"
            SearchStats.claude_calls += 1
            
            # Сохраняем в историю
            messages.append({
                'role': 'assistant',
                'content': answer
            })
            
            await state.update_data(messages=messages)
            
            logger.info(f"✓ Claude Answer")
        
        # STEP 3: Отправляем ответ пользователю
        await message.answer(answer)
        
        # STEP 4: Сохраняем в БД для learning loop
        await save_conversation(
            user_id=user_id,
            question=user_text,
            answer=answer,
            source=source,
            confidence=search_results[0]['score'] if search_results else 0
        )
        
        # STEP 5: Обновляем статистику токенов
        if search_results:
            SearchStats.tokens_saved += search_results[0].get('compression_ratio', 0)
    
    except Exception as e:
        logger.error(f"Error in AI chat: {e}")
        await message.answer(
            "Извините, произошла ошибка. Попробуйте позже или свяжитесь с администратором."
        )


async def save_conversation(user_id: int, question: str, answer: str, source: str, confidence: float):
    """
    Сохраняем разговор для learning loop
    
    Используется для:
    - Отслеживания часто задаваемых вопросов
    - Автоматического создания FAQ
    - Улучшения поиска со временем
    """
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Проверяем есть ли таблица conversations
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                question TEXT,
                answer TEXT,
                source TEXT,
                confidence REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            INSERT INTO conversations (user_id, question, answer, source, confidence)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, question, answer, source, confidence))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Conversation saved (source: {source}, confidence: {confidence:.2%})")
    
    except Exception as e:
        logger.error(f"Error saving conversation: {e}")


def get_stats() -> dict:
    """Получить статистику поисков"""
    
    if SearchStats.total_searches == 0:
        return {"error": "No searches yet"}
    
    return {
        "total_searches": SearchStats.total_searches,
        "db_answers": SearchStats.db_answers,
        "claude_calls": SearchStats.claude_calls,
        "db_answer_rate": f"{100 * SearchStats.db_answers / SearchStats.total_searches:.1f}%",
        "tokens_saved_approx": SearchStats.tokens_saved,
        "efficiency": "High" if SearchStats.db_answer_rate > 70 else "Medium" if SearchStats.db_answers > 50 else "Low"
    }
