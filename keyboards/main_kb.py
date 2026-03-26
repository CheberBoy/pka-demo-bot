from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📅 Записаться"), KeyboardButton(text="💅 Наши услуги")],
            [KeyboardButton(text="💬 Задать вопрос"), KeyboardButton(text="📞 Контакты")],
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )
