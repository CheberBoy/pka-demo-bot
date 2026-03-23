import asyncio
import logging
from aiogram.types import BotCommand
from create_bot import bot, dp
from db.database import init_db
from utils.scheduler import setup_scheduler
from handlers import start, booking, ai_chat

logging.basicConfig(level=logging.INFO)

async def main():
    # Инициализировать БД
    await init_db()

    # Зарегистрировать команды — появятся в меню (≡) слева внизу
    await bot.set_my_commands([
        BotCommand(command="book", description="📅 Записаться"),
        BotCommand(command="contacts", description="📞 Контакты"),
    ])

    # Подключить роутеры
    dp.include_router(start.router)
    dp.include_router(booking.router)
    dp.include_router(ai_chat.router)  # ai_chat ПОСЛЕДНИМ (ловит всё)

    # Запустить планировщик напоминаний
    setup_scheduler(bot)

    # Запустить бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
