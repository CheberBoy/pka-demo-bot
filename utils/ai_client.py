import logging
from anthropic import AsyncAnthropic
from config import ANTHROPIC_API_KEY, SYSTEM_PROMPT, SALON_PHONE

client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

async def get_ai_response(messages: list, is_new_user: bool = True) -> str:
    """Получить ответ от Claude на вопрос клиента"""
    system = SYSTEM_PROMPT
    if not is_new_user:
        system += "\nВАЖНО: Это уже знакомый клиент — не здоровайся, сразу отвечай по существу."
    try:
        response = await client.messages.create(
            model="claude-3-5-haiku-latest",
            max_tokens=512,
            system=system,
            messages=messages
        )
        return response.content[0].text
    except Exception as e:
        logging.error(f"Claude API error: {e}")
        return "Извините, ИИ временно недоступен. Позвоните нам: " + SALON_PHONE
