from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from utils.sqlite_storage import SQLiteStorage

bot = Bot(token=BOT_TOKEN)
storage = SQLiteStorage()
dp = Dispatcher(storage=storage)
