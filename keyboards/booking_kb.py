from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import SERVICES, MASTERS, TIME_SLOTS

def get_services_keyboard():
    buttons = []
    for service, price in SERVICES.items():
        buttons.append([InlineKeyboardButton(
            text=f"{service} — {price} сом",
            callback_data=f"service:{service}"
        )])
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_masters_keyboard():
    buttons = []
    row = []
    for master in MASTERS:
        row.append(InlineKeyboardButton(text=master, callback_data=f"master:{master}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_dates_keyboard():
    from datetime import datetime, timedelta
    buttons = []
    today = datetime.now()
    for i in range(1, 8):  # Следующие 7 дней
        day = today + timedelta(days=i)
        label = day.strftime("%d %b (%a)")
        value = day.strftime("%Y-%m-%d")
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"date:{value}")])
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_times_keyboard():
    buttons = []
    row = []
    for slot in TIME_SLOTS:
        row.append(InlineKeyboardButton(text=slot, callback_data=f"time:{slot}"))
        if len(row) == 4:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
