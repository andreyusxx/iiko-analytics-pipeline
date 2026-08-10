import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from dotenv import load_dotenv
# Імпортуємо наші функції з database.py
from database import get_connection, add_employee, register_shift

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Описуємо стани для процесу додавання працівника
class AddEmployee(StatesGroup):
    name = State()
    role = State()
    rate = State()

# Команда /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    # Створюємо просту клавіатуру з кнопками
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="👥 Список працівників"), types.KeyboardButton(text="➕ Додати працівника")]
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

# Запуск бота
async def main():
    print("Бот запущений і готовий приймати повідомлення...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())