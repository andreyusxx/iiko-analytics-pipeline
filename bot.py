import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from dotenv import load_dotenv
# Імпортуємо наші функції з database.py
from database import get_connection, add_employee, get_today_shifts, register_shift, toggle_shift, update_employee
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import get_unpaid_shifts, mark_all_unpaid_as_paid
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Описуємо стани для процесу додавання працівника
class AddEmployee(StatesGroup):
    name = State()
    role = State()
    rate = State()

class UpdateEmployee(StatesGroup):
    emp_id = State()
    name = State()
    role = State()
    rate = State()

class PaymentPeriod(StatesGroup):
    start_date = State()
    end_date = State()

# Команда /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    # Створюємо просту клавіатуру з кнопками
    keyboard = types.ReplyKeyboardMarkup(
    keyboard=[
        [types.KeyboardButton(text="👥 Список працівників"), types.KeyboardButton(text="➕ Додати працівника")],
        [types.KeyboardButton(text="✏️ Редагувати працівника"), types.KeyboardButton(text="📅 Управління змінами")],
        [types.KeyboardButton(text="🔍 Хто сьогодні працює?"), types.KeyboardButton(text="💰 Зарплати та борги")],
        [types.KeyboardButton(text="💰 Закрити тиждень (вибрати період)")]
    ],
    resize_keyboard=True
)
    await message.answer(
        "Обери потрібну дію:",
        reply_markup=keyboard
    )

# Обробник кнопки "Список працівників"
@dp.message(F.text == "👥 Список працівників")
async def show_employees(message: types.Message):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, full_name, role, daily_rate FROM employees;")
        rows = cur.fetchall()
        
        if not rows:
            await message.answer("У базі поки немає жодного працівника.")
            return

        response = "📋 **Список персоналу:**\n\n"
        for row in rows:
            emp_id, name, role, rate = row
            response += f"ID: {emp_id} | {name} ({role}) — Ставка: {rate} грн/день\n"
            
        # Форматуємо рядок виводу
        text_output = "".join(response)
        await message.answer(text_output, parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"Помилка при отриманні даних: {e}")
    finally:
        cur.close()
        conn.close()

# Крок 1: Початок додавання працівника
@dp.message(F.text == "➕ Додати працівника")
async def start_add_employee(message: types.Message, state: FSMContext):
    await state.set_state(AddEmployee.name)
    await message.answer("Введи ПІБ нового працівника:")

# Крок 2: Отримання імені та запит посади
@dp.message(AddEmployee.name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(AddEmployee.role)
    await message.answer("Введи посаду (наприклад: hookah, waiter, bartender, admin):")

# Крок 3: Отримання посади та запит ставки
@dp.message(AddEmployee.role)
async def process_role(message: types.Message, state: FSMContext):
    await state.update_data(role=message.text)
    await state.set_state(AddEmployee.rate)
    await message.answer("Введи денну ставку (тільки число, наприклад 1500):")

# Крок 4: Отримання ставки і збереження в Neon
@dp.message(AddEmployee.rate)
async def process_rate(message: types.Message, state: FSMContext):
    try:
        rate = float(message.text)
        data = await state.get_data()
        
        # Зберігаємо через функцію бази даних
        add_employee(data['name'], data['role'], rate)
        
        await message.answer(
            f"✅ Працівника успішно додано!\n\n"
            f"👤 ПІБ: {data['name']}\n"
            f"💼 Посада: {data['role']}\n"
            f"💰 Ставка: {rate} грн/день"
        )
        await state.clear()
    except ValueError:
        await message.answer("❌ Будь ласка, введи коректне числове значення для ставки (наприклад, 1500 або 1200.50):")

# Крок 1: Початок редагування (просимо ID)
@dp.message(F.text == "✏️ Редагувати працівника")
async def start_update_employee(message: types.Message, state: FSMContext):
    await state.set_state(UpdateEmployee.emp_id)
    await message.answer("Введи **ID** працівника:", parse_mode="Markdown")

# Крок 2: Зберігаємо ID та запитуємо нове ім'я
@dp.message(UpdateEmployee.emp_id)
async def process_update_id(message: types.Message, state: FSMContext):
    try:
        emp_id = int(message.text)
        await state.update_data(emp_id=emp_id)
        await state.set_state(UpdateEmployee.name)
        await message.answer("Введи ПІБ працівника:")
    except ValueError:
        await message.answer("❌ ID має бути цілим числом. Спробуй ще раз ввести ID:")

# Крок 3: Отримуємо нове ім'я та запитуємо нову посаду
@dp.message(UpdateEmployee.name)
async def process_update_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(UpdateEmployee.role)
    await message.answer("Введи нову посаду:")

# Крок 4: Отримуємо нову посаду та запитуємо нову ставку
@dp.message(UpdateEmployee.role)
async def process_update_role(message: types.Message, state: FSMContext):
    await state.update_data(role=message.text)
    await state.set_state(UpdateEmployee.rate)
    await message.answer("Введи нову денну ставку:")

# Крок 5: Зберігаємо зміни в базу даних Neon
@dp.message(UpdateEmployee.rate)
async def process_update_rate(message: types.Message, state: FSMContext):
    try:
        rate = float(message.text)
        data = await state.get_data()
        
        # Викликаємо функцію оновлення
        update_employee(data['emp_id'], data['name'], data['role'], rate)
        
        await message.answer(
            f"✅ Дані працівника успішно оновлено!\n\n"
            f"🆔 ID: {data['emp_id']}\n"
            f"👤 ПІБ: {data['name']}\n"
            f"💼 Посада: {data['role']}\n"
            f"💰 Нова ставка: {rate} грн/день"
        )
        await state.clear()
    except Exception as e:
        await message.answer(f"❌ Помилка: {e}")

# Кнопка для адміна
@dp.message(F.text == "📅 Управління змінами")
async def admin_shift_menu(message: types.Message):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, full_name FROM employees;")
    rows = cur.fetchall()
    
    # Створюємо клавіатуру з іменами
    buttons = []
    for emp_id, name in rows:
        buttons.append([InlineKeyboardButton(text=name, callback_data=f"toggle_{emp_id}")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("Обери працівників, які сьогодні працюють:", reply_markup=keyboard)
    cur.close()
    conn.close()

# Обробка натискань на кнопки
@dp.callback_query(F.data.startswith("toggle_"))
async def callback_toggle(callback: types.CallbackQuery):
    emp_id = int(callback.data.split("_")[1])
    status = toggle_shift(emp_id)
    
    # Оновлюємо повідомлення (коротка відповідь)
    await callback.answer(f"Статус змінено: {status}")

# Перегляд неоплачених змін і боргів
@dp.message(F.text == "💰 Зарплати та борги")
async def show_payroll_debts(message: types.Message):
    rows = get_unpaid_shifts()
    if not rows:
        await message.answer("✅ Усі зміни повністю оплачені! Неоплачених боргів немає.")
        return

    response = "💰 **Неоплачені зміни та борги по ЗП:**\n\n"
    total_all = 0
    for row in rows:
        name, days, debt = row
        response += f"👤 **{name}**\n   • Відпрацьовано днів: {days}\n   • Сума до виплати: {debt} грн\n\n"
        total_all += debt

    response += f"💵 **Загальна сума всіх боргів:** {total_all} грн"
    await message.answer(response, parse_mode="Markdown")


@dp.message(F.text == "🔍 Хто сьогодні працює?")
async def show_today_shifts(message: types.Message):
    rows = get_today_shifts()
    if not rows:
        await message.answer("Сьогодні на зміні нікого немає.")
        return
        
    response = "🗓 **Сьогодні на зміні:**\n\n"
    for name, role in rows:
        response += f"👤 {name} ({role})\n"
    await message.answer(response, parse_mode="Markdown")

@dp.message(F.text == "💰 Закрити тиждень (вибрати період)")
async def start_payment_period(message: types.Message, state: FSMContext):
    await state.set_state(PaymentPeriod.start_date)
    await message.answer("Введи дату ПОЧАТКУ періоду (у форматі YYYY-MM-DD):")

@dp.message(PaymentPeriod.start_date)
async def process_start_date(message: types.Message, state: FSMContext):
    await state.update_data(start_date=message.text)
    await state.set_state(PaymentPeriod.end_date)
    await message.answer("Введи дату КІНЦЯ періоду (у форматі YYYY-MM-DD):")

@dp.message(PaymentPeriod.end_date)
async def process_end_date(message: types.Message, state: FSMContext):
    end_date = message.text
    data = await state.get_data()
    start_date = data['start_date']
    
    # Викликаємо функцію оплати
    count = mark_all_unpaid_as_paid(start_date, end_date)
    
    await message.answer(f"✅ Готово! Позначено як оплачені {count} змін(и) у період з {start_date} по {end_date}.")
    await state.clear()

# Запуск бота
async def main():
    print("Бот запущений і готовий приймати повідомлення...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())