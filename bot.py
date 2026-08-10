import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from dotenv import load_dotenv

# Імпортуємо наші функції з database.py
from database import get_connection, add_employee, register_shift

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()

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
        "Привіт! Я бот для обліку змін та зарплат ресторану 📊\nОбери потрібну дію на клавіатурі нижче:",
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
            response.append(f"ID: {emp_id} | {name} ({role}) — Ставка: {rate} грн/день\n")
            
        # Форматуємо рядок виводу
        text_output = "".join(response)
        await message.answer(text_output, parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"Помилка при отриманні даних: {e}")
    finally:
        cur.close()
        conn.close()

# Запуск бота
async def main():
    print("Бот запущений і готовий приймати повідомлення...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())