import logging
from anthropic import AsyncAnthropic
from config import ANTHROPIC_API_KEY, SYSTEM_PROMPT, SALON_PHONE

client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

async def get_ai_response(messages: list) -> str:
    """Получить ответ от Claude на вопрос клиента"""
    try:
        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            system=SYSTEM_PROMPT,
            messages=messages
        )
        return response.content[0].text
    except Exception as e:
        logging.error(f"Claude API error: {e}")
        return "Извините, ИИ временно недоступен. Позвоните нам: " + SALON_PHONE
