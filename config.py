import json
import os
from decouple import config

# Telegram
BOT_TOKEN = config('BOT_TOKEN')
ANTHROPIC_API_KEY = config('ANTHROPIC_API_KEY')
ADMIN_CHAT_ID = config('ADMIN_CHAT_ID', cast=int)

# Загружаем данные салона: сначала из salon_data.json, иначе дефолтные
_SALON_JSON = os.path.join(os.path.dirname(__file__), 'salon_data.json')

if os.path.exists(_SALON_JSON):
    with open(_SALON_JSON, encoding='utf-8') as f:
        _data = json.load(f)

    SALON_NAME    = _data.get('name') or "Салон красоты"
    SALON_PHONE   = _data.get('phone') or "+996 555 000 000"
    SALON_ADDRESS = _data.get('address') or ""
    SALON_HOURS   = _data.get('hours') or "09:00 — 19:00, каждый день"
    SALON_ABOUT   = _data.get('about') or ""

    MASTERS = [
        m['name'] if isinstance(m, dict) else m
        for m in _data.get('masters', [])
    ]

    SERVICES = {
        s['name']: s.get('price') or 0
        for s in _data.get('services', [])
    }

    _SERVICES_TEXT = '\n'.join(
        f"  • {s['name']} — {s.get('price_text') or (str(s['price']) + ' сом') if s.get('price') else 'уточнить'}"
        for s in _data.get('services', [])
    )

    _MASTERS_TEXT = ', '.join(
        (f"{m['name']} ({m['specialty']})" if isinstance(m, dict) and m.get('specialty') else
         (m['name'] if isinstance(m, dict) else m))
        for m in _data.get('masters', [])
    ) or "наши специалисты"

    _FAQ_TEXT = '\n'.join(
        f"  В: {faq['question']}\n  О: {faq['answer']}"
        for faq in _data.get('faq', [])
    )

else:
    # Дефолтные данные (демо-режим)
    SALON_NAME    = "Салон красоты Glamour"
    SALON_PHONE   = "+996 555 123 456"
    SALON_ADDRESS = "Бишкек (адрес уточните по телефону)"
    SALON_HOURS   = "09:00 — 19:00, каждый день"
    SALON_ABOUT   = "Уютный салон красоты в Бишкеке."

    MASTERS = ["Айгуль", "Динара", "Назгуль"]

    SERVICES = {
        "Стрижка": 500,
        "Окрашивание": 2000,
        "Маникюр": 600,
        "Педикюр": 700,
        "Брови": 400,
    }

    _SERVICES_TEXT = '\n'.join(f"  • {s} — {p} сом" for s, p in SERVICES.items())
    _MASTERS_TEXT  = ', '.join(MASTERS)
    _FAQ_TEXT      = ""

# Расписание (каждые 30 минут с 9:00 до 19:00)
TIME_SLOTS = [
    "09:00", "09:30", "10:00", "10:30", "11:00", "11:30",
    "12:00", "12:30", "13:00", "13:30", "14:00", "14:30",
    "15:00", "15:30", "16:00", "16:30", "17:00", "17:30",
    "18:00", "18:30",
]

# Системный промпт — строится из реальных данных салона
SYSTEM_PROMPT = f"""Ты — AI-администратор салона "{SALON_NAME}". Тебя зовут Айя.

О салоне:
{SALON_ABOUT}

Твой характер:
- Тёплая и дружелюбная, как подруга которая разбирается в красоте
- Отвечаешь естественно, не как робот — можешь добавить лёгкую шутку
- Если клиент просто болтает — поддержи разговор, не гони сразу к записи
- Если хочет записаться — скажи: "Нажми кнопку 📅 Записаться — она внизу"
- НИКОГДА не здоровайся повторно в течение диалога — только в первом ответе

Ты знаешь всё о салоне:
Услуги и цены:
{_SERVICES_TEXT}

Мастера: {_MASTERS_TEXT}
Телефон: {SALON_PHONE}
Адрес: {SALON_ADDRESS}
Часы работы: {SALON_HOURS}
{f"Частые вопросы:{chr(10)}{_FAQ_TEXT}" if _FAQ_TEXT else ""}

Отвечай на русском языке. Будь краткой — максимум 3-4 предложения.
Можешь отвечать на общие вопросы о красоте и уходе — это твоя тема.
"""
