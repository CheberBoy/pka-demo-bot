from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from db.database import get_bookings_for_reminder

scheduler = AsyncIOScheduler()

def setup_scheduler(bot: Bot):
    """Запускает планировщик напоминаний"""
    scheduler.add_job(
        send_reminders,
        'interval',
        minutes=1,  # Проверяем каждую минуту
        args=[bot]
    )
    scheduler.start()

async def send_reminders(bot: Bot):
    """Отправляет напоминания клиентам за 2 часа до визита"""
    bookings = await get_bookings_for_reminder()
    for booking in bookings:
        try:
            await bot.send_message(
                booking['client_id'],
                f"⏰ Напоминание!\n\n"
                f"Через 2 часа вас ждём на {booking['service']}\n"
                f"👩 Мастер: {booking['master']}\n"
                f"🕐 Время: {booking['time']}\n\n"
                f"Ждём вас! 💅"
            )
        except Exception:
            pass  # Если пользователь заблокировал бота
