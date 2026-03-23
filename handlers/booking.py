from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram import Bot
from config import ADMIN_CHAT_ID, SALON_NAME
from keyboards.main_kb import get_main_keyboard
from keyboards.booking_kb import (
    get_services_keyboard, get_masters_keyboard,
    get_dates_keyboard, get_times_keyboard
)
from db.database import add_booking

router = Router()

class BookingState(StatesGroup):
    choosing_service = State()
    choosing_master = State()
    choosing_date = State()
    choosing_time = State()
    entering_name = State()

# ── ВХОД В ЗАПИСЬ ────────────────────────────────────────────
@router.message(F.text == "📅 Записаться")
async def start_booking(message: Message, state: FSMContext):
    await state.set_state(BookingState.choosing_service)
    await message.answer("Выберите услугу:", reply_markup=get_services_keyboard())

# ── ОТМЕНА ────────────────────────────────────────────────────
@router.callback_query(F.data == "cancel")
async def cancel_booking(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.delete()
    await call.message.answer(
        "Запись отменена. Чем могу помочь?",
        reply_markup=get_main_keyboard()
    )
    await call.answer()

# ── ШАГ 1: Выбор услуги ──────────────────────────────────────
@router.callback_query(BookingState.choosing_service, F.data.startswith("service:"))
async def process_service(call: CallbackQuery, state: FSMContext):
    service = call.data.split(":")[1]
    await state.update_data(service=service)
    await state.set_state(BookingState.choosing_master)
    await call.message.edit_text(
        f"✅ Услуга: {service}\n\nВыберите мастера:",
        reply_markup=get_masters_keyboard()
    )
    await call.answer()

# ── ШАГ 2: Выбор мастера ────────────────────────────────────
@router.callback_query(BookingState.choosing_master, F.data.startswith("master:"))
async def process_master(call: CallbackQuery, state: FSMContext):
    master = call.data.split(":")[1]
    await state.update_data(master=master)
    await state.set_state(BookingState.choosing_date)
    data = await state.get_data()
    await call.message.edit_text(
        f"✅ Услуга: {data['service']}\n"
        f"✅ Мастер: {master}\n\n"
        f"Выберите дату:",
        reply_markup=get_dates_keyboard()
    )
    await call.answer()

# ── ШАГ 3: Выбор даты ───────────────────────────────────────
@router.callback_query(BookingState.choosing_date, F.data.startswith("date:"))
async def process_date(call: CallbackQuery, state: FSMContext):
    date = call.data.split(":")[1]
    await state.update_data(date=date)
    await state.set_state(BookingState.choosing_time)
    data = await state.get_data()
    await call.message.edit_text(
        f"✅ Услуга: {data['service']}\n"
        f"✅ Мастер: {data['master']}\n"
        f"✅ Дата: {date}\n\n"
        f"Выберите время:",
        reply_markup=get_times_keyboard()
    )
    await call.answer()

# ── ШАГ 4: Выбор времени ────────────────────────────────────
@router.callback_query(BookingState.choosing_time, F.data.startswith("time:"))
async def process_time(call: CallbackQuery, state: FSMContext):
    time = call.data.split(":")[1]
    await state.update_data(time=time)
    await state.set_state(BookingState.entering_name)
    data = await state.get_data()
    await call.message.edit_text(
        f"✅ Услуга: {data['service']}\n"
        f"✅ Мастер: {data['master']}\n"
        f"✅ Дата: {data['date']}\n"
        f"✅ Время: {time}\n\n"
        f"Введите ваше имя:"
    )
    await call.answer()

# ── ШАГ 5: Имя + Финальное подтверждение ────────────────────
@router.message(BookingState.entering_name)
async def process_name(message: Message, state: FSMContext, bot: Bot):
    name = message.text.strip()
    data = await state.get_data()

    # Сохранить в базу
    booking_id = await add_booking(
        client_name=name,
        client_id=message.from_user.id,
        service=data['service'],
        master=data['master'],
        date=data['date'],
        time=data['time']
    )

    await state.clear()

    # Подтверждение клиенту
    await message.answer(
        f"🎉 Запись подтверждена!\n\n"
        f"👤 Имя: {name}\n"
        f"💅 Услуга: {data['service']}\n"
        f"👩 Мастер: {data['master']}\n"
        f"📅 Дата: {data['date']}\n"
        f"🕐 Время: {data['time']}\n\n"
        f"Ждём вас! Напомним за 2 часа до визита 🔔",
        reply_markup=get_main_keyboard()
    )

    # Уведомление владельцу
    await bot.send_message(
        ADMIN_CHAT_ID,
        f"📋 НОВАЯ ЗАПИСЬ #{booking_id}\n\n"
        f"👤 Клиент: {name} (@{message.from_user.username or 'нет'})\n"
        f"💅 Услуга: {data['service']}\n"
        f"👩 Мастер: {data['master']}\n"
        f"📅 Дата: {data['date']}\n"
        f"🕐 Время: {data['time']}"
    )
