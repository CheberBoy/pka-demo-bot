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

class SalonDatabaseSearch:
    """Simple database search without external dependencies"""
    
    def __init__(self, db_path):
        self.db_path = db_path
    
    def search_services(self, query):
        """Search for services"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query_lower = query.lower()
            
            cursor.execute("""
                SELECT name, price, duration_minutes, description
                FROM services
                WHERE LOWER(name) LIKE ? OR LOWER(description) LIKE ?
                LIMIT 3
            """, (f'%{query_lower}%', f'%{query_lower}%'))
            
            results = cursor.fetchall()
            conn.close()
            
            if results:
                return {
                    'type': 'service',
                    'data': results,
                    'score': 0.85
                }
        except Exception as e:
            logger.error(f"Service search error: {e}")
        
        return None
    
    def search_masters(self, query):
        """Search for masters"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query_lower = query.lower()
            
            cursor.execute("""
                SELECT name, specialty, experience_years, rating
                FROM masters
                WHERE LOWER(name) LIKE ? OR LOWER(specialty) LIKE ?
                LIMIT 3
            """, (f'%{query_lower}%', f'%{query_lower}%'))
            
            results = cursor.fetchall()
            conn.close()
            
            if results:
                return {
                    'type': 'master',
                    'data': results,
                    'score': 0.80
                }
        except Exception as e:
            logger.error(f"Master search error: {e}")
        
        return None
    
    def search_faq(self, query):
        """Search FAQ"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query_lower = query.lower()
            
            cursor.execute("""
                SELECT question, answer
                FROM faq
                WHERE LOWER(question) LIKE ? OR LOWER(answer) LIKE ?
                LIMIT 1
            """, (f'%{query_lower}%', f'%{query_lower}%'))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return {
                    'type': 'faq',
                    'data': result,
                    'score': 0.95
                }
        except Exception as e:
            logger.error(f"FAQ search error: {e}")
        
        return None
    
    def get_hours(self):
        """Get working hours"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT day_of_week, open_time, close_time
                FROM working_hours
                ORDER BY CASE day_of_week
                    WHEN 'monday' THEN 1
                    WHEN 'tuesday' THEN 2
                    WHEN 'wednesday' THEN 3
                    WHEN 'thursday' THEN 4
                    WHEN 'friday' THEN 5
                    WHEN 'saturday' THEN 6
                    WHEN 'sunday' THEN 7
                END
            """)
            
            results = cursor.fetchall()
            conn.close()
            
            if results:
                return {
                    'type': 'hours',
                    'data': results,
                    'score': 0.99
                }
        except Exception as e:
            logger.error(f"Hours search error: {e}")
        
        return None


# Initialize search
db_search = SalonDatabaseSearch(str(DB_PATH))

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
    Handle message with database search first, Claude fallback
    """
    
    try:
        user_id = message.from_user.id
        user_text = getattr(message, 'override_text', message.text)
        user_text = (user_text or message.caption or "").strip()
        
        logger.info(f"User {user_id}: {user_text}")
        
        # STEP 1: Try FAQ first (most likely to have answer)
        faq_result = db_search.search_faq(user_text)
        if faq_result and faq_result['score'] > 0.8:
            answer = faq_result['data'][1]  # FAQ answer
            source = "faq"
            logger.info(f"✓ FAQ Answer (confidence: {faq_result['score']:.0%})")
        
        # STEP 2: Try service search
        elif 'услуг' in user_text.lower() or 'стоим' in user_text.lower() or any(w in user_text.lower() for w in ['стрижка', 'окраш', 'маник', 'пед', 'ресниц', 'бров', 'макияж']):
            service_result = db_search.search_services(user_text)
            if service_result and service_result['score'] > 0.75:
                service = service_result['data'][0]
                answer = f"*{service[0]}*\n💰 {service[1]} сом\n⏱ {service[2]} минут\n\n{service[3]}"
                source = "service_db"
                logger.info(f"✓ Service Answer")
            else:
                answer = "Извините, я не нашел эту услугу в базе. Пожалуйста, спросите конкретно какую услугу вас интересует."
                source = "error"
        
        # STEP 3: Try master search
        elif any(w in user_text.lower() for w in ['мастер', 'специалист', 'айгуль', 'динара', 'назгуль', 'гулмира']):
            master_result = db_search.search_masters(user_text)
            if master_result and master_result['score'] > 0.75:
                master = master_result['data'][0]
                answer = f"*{master[0]}* - _{master[1]}_\n⭐ {master[3]}/5 ⭐\n📊 Опыт: {master[2]} лет"
                source = "master_db"
                logger.info(f"✓ Master Answer")
            else:
                answer = "Извините, я не нашел этого мастера. Спросите про конкретного мастера или услугу."
                source = "error"
        
        # STEP 4: Check for hours/schedule
        elif any(w in user_text.lower() for w in ['время', 'часы', 'когда', 'открыт', 'закрыт']):
            hours_result = db_search.get_hours()
            if hours_result:
                hours_text = "⏰ *Расписание*:\n"
                for day, open_t, close_t in hours_result['data']:
                    day_rus = {
                        'monday': 'Пн',
                        'tuesday': 'Вт',
                        'wednesday': 'Ср',
                        'thursday': 'Чт',
                        'friday': 'Пт',
                        'saturday': 'Сб',
                        'sunday': 'Вс'
                    }.get(day, day)
                    hours_text += f"{day_rus}: {open_t}-{close_t}\n"
                answer = hours_text
                source = "hours_db"
                logger.info(f"✓ Hours Answer")
            else:
                answer = "К сожалению, я не могу получить информацию о расписании."
                source = "error"
        
        # STEP 5: Default - ask Claude AI
        else:
            known = await is_known_user(user_id)
            if not known:
                await register_user(user_id)

            data = await state.get_data()
            history = data.get("chat_history", [])
            history.append({"role": "user", "content": user_text})
            if len(history) > 20:
                history = history[-20:]

            await message.chat.do("typing")
            answer = await get_ai_response(history, is_new_user=not known)

            history.append({"role": "assistant", "content": answer})
            await state.update_data(chat_history=history)
            source = "claude"
        
        # Send answer
        await message.answer(answer)
        
        # Log conversation
        logger.info(f"Response ({source}): {answer[:50]}...")
    
    except Exception as e:
        logger.error(f"Error: {e}")
        await message.answer("Извините, произошла ошибка. Попробуйте позже.")
