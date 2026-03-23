import aiosqlite
from datetime import datetime

DB_PATH = "salon.db"

async def init_db():
    """Создаёт таблицы при первом запуске"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_name TEXT NOT NULL,
                client_id INTEGER NOT NULL,
                service TEXT NOT NULL,
                master TEXT NOT NULL,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                status TEXT DEFAULT 'confirmed',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()

async def add_booking(client_name, client_id, service, master, date, time):
    """Добавить запись клиента"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """INSERT INTO bookings
               (client_name, client_id, service, master, date, time)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (client_name, client_id, service, master, date, time)
        )
        await db.commit()
        return cursor.lastrowid

async def get_bookings_for_reminder():
    """Получить записи, которым через 2 часа визит"""
    now = datetime.now()
    target_time = f"{(now.hour + 2) % 24:02d}:{now.minute:02d}"
    today = now.strftime("%Y-%m-%d")

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT * FROM bookings
               WHERE date = ? AND time = ? AND status = 'confirmed'""",
            (today, target_time)
        )
        return await cursor.fetchall()
