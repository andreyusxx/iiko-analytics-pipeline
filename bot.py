import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from dotenv import load_dotenv
# Імпортуємо наші функції з database.py
from database import get_aggregated_payroll, get_connection, add_employee, get_today_shifts, register_shift, toggle_shift, update_employee
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import get_unpaid_shifts, mark_all_unpaid_as_paid, get_report_for_dates, delete_employee_by_id
from storage import upload_payroll_report
from datetime import datetime
from middleware import AdminMiddleware
from aiogram.utils.keyboard import InlineKeyboardBuilder
import openai


load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

bot = Bot(token=TOKEN)
client = openai.OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.getenv("GROQ_API_KEY")
)
dp = Dispatcher()
dp.message.outer_middleware(AdminMiddleware())

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

class AIAgentStates(StatesGroup):
    waiting_for_question = State()

# Команда /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    # Створюємо просту клавіатуру з кнопками
    keyboard = types.ReplyKeyboardMarkup(
    keyboard=[
        [types.KeyboardButton(text="👥 Список працівників"), types.KeyboardButton(text="➕ Додати працівника")],
        [types.KeyboardButton(text="✏️ Редагувати працівника"), types.KeyboardButton(text="📅 Управління змінами")],
        [types.KeyboardButton(text="🔍 Хто сьогодні працює?"), types.KeyboardButton(text="💰 Зарплати та борги")],
        [types.KeyboardButton(text="💰 Закрити тиждень (вибрати період)"), types.KeyboardButton(text="🤖 AI Аналітик")]
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
        cur.execute("SELECT id, full_name, position, hourly_rate FROM syrve_employees;")
        rows = cur.fetchall()
        
        if not rows:
            await message.answer("У базі поки немає жодного працівника.")
            return

        response = "📋 **Список персоналу:**\n\n"
        keyboard = InlineKeyboardBuilder()
        for row in rows:
            emp_id, name, role, rate = row
            response += f"{name} ({role}) — Ставка: {rate} грн/день\n"

            keyboard.button(
                text=f"🗑 Видалити {name.split()[0]}", # Скоротимо текст кнопки для зручності
                callback_data=f"del_employee_{emp_id}"
            )
        keyboard.adjust(1)
            
        await message.answer(
            response, 
            reply_markup=keyboard.as_markup(), 
            parse_mode="Markdown"
        )
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
    await message.answer("Введи посаду:")

# Крок 3: Отримання посади та запит ставки
@dp.message(AddEmployee.role)
async def process_role(message: types.Message, state: FSMContext):
    await state.update_data(role=message.text)
    await state.set_state(AddEmployee.rate)
    await message.answer("Введи денну ставку:")

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
    cur.execute("SELECT id, full_name FROM syrve_employees;")
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
    emp_id = callback.data.split("_")[1]
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

    try:

        aggregated_data = get_aggregated_payroll(start_date, end_date)
        
        if not aggregated_data:
            await message.answer("⚠️ За вказаний період не знайдено неоплачених змін.")
            await state.clear()
            return
        
        await state.update_data(end_date=end_date)

        report_text = f"📊 **Попередній розрахунок виплат ({start_date} — {end_date}):**\n\n"
        grand_total = 0
        for item in aggregated_data:
            report_text += f"• **{item['employee_name']}**: {item['total']} грн ({item['shifts_count']} змін)\n"
            grand_total += item['total']
        
        report_text += f"\n💰 **Загальна сума до виплати:** {grand_total} грн"

        # Створюємо кнопку підтвердження
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Підтвердити і закрити", callback_data="confirm_payroll"),
                InlineKeyboardButton(text="❌ Скасувати", callback_data="cancel_payroll")
            ]
        ])

        await message.answer(report_text, parse_mode="Markdown", reply_markup=keyboard)

    except Exception as e:
        await message.answer(f"❌ Помилка під час формування звіту: {e}")
        await state.clear()

@dp.callback_query(F.data == "confirm_payroll")
async def confirm_payroll_handler(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    start_date = data.get('start_date')
    end_date = data.get('end_date')

    try:
        # Витягуємо повні сирі дані для R2
        report_data = get_report_for_dates(start_date, end_date)
        
        # Завантаження в Cloudflare R2
        filename = f"payroll_{start_date}_{end_date}_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        upload_payroll_report(report_data, filename)

        # Оновлення статусу в базі (тільки неоплачені за цей період)
        count = mark_all_unpaid_as_paid(start_date, end_date)

        await callback.message.edit_text(
            f"✅ **Період успішно закрито!**\n"
            f"• Звіт вивантажено в R2: `payroll_reports/{filename}`\n"
            f"• Позначено як оплачені: {count} змін(и) у період з {start_date} по {end_date}.",
            parse_mode="Markdown"
        )
    except Exception as e:
        await callback.message.edit_text(f"❌ Помилка під час закриття періоду: {e}")
    
    await state.clear()
    await callback.answer()


@dp.callback_query(F.data == "cancel_payroll")
async def cancel_payroll_handler(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("❌ Операцію закриття періоду скасовано.")
    await state.clear()
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("del_employee_"))
async def callback_delete_employee(callback: types.CallbackQuery):
    employee_id = callback.data.split("_")[2]
    
    try:
        delete_employee_by_id(employee_id)
        await callback.message.edit_text(f"✅ Працівника з ID {employee_id} успішно видалено з бази даних.")
    except Exception as e:
        await callback.message.answer(f"❌ Помилка під час видалення працівника: {e}")
    
    await callback.answer()

@dp.message(F.text == "🤖 AI Аналітик")
async def ai_analyst_start(message: types.Message, state: FSMContext):
    await state.set_state(AIAgentStates.waiting_for_question)
    await message.answer("Я твій AI-аналітик. Напиши будь-яке запитання:")

@dp.message(AIAgentStates.waiting_for_question)
async def process_ai_question(message: types.Message, state: FSMContext):
    user_question = message.text
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    # Описуємо схему бази даних для LLM, щоб вона знала структуру
    db_schema = """
    Tables and Views in public schema:
    1. syrve_employees (id, full_name, position, hourly_rate)
    2. staff_shifts (id, employee_id, shift_date, is_paid, shift_rate)
    3. processed_files (file_name, processed_at)
    4. silver_guest_checks (id, uniq_order_id, order_num, session_num, table_num, cashier, dish_name, dish_sum, discount_sum, open_time, close_time, pay_types, category_name, source_file)
    5. syrve_categories (id, name, description)
    6. syrve_products (id, sku, name, description, category_id, category_name)
    7. gold_daily_sales (sale_date, total_orders, total_sold_items, gross_revenue, total_discounts, net_revenue)
    8. gold_top_dishes (dish_name, times_ordered, total_revenue)
    9. gold_cashier_performance (cashier, orders_handled, revenue_generated)
    10. gold_revenue_by_category (category_name, items_sold, total_revenue)
    """
    
    try:
        system_prompt = (
            "Ти експерт з PostgreSQL для ресторанного бізнесу. "
            "Поверни ВИКЛЮЧНО чистий SQL-запит без форматування markdown (без ```sql). "
            "Починай одразу з SELECT. "
            "Для днів тижня використовуй функцію EXTRACT(ISODOW FROM shift_date) або TO_CHAR(date, 'Day'). "
            "ЗАВЖДИ додавай у кінці запиту LIMIT 20 (або менше), якщо виводиш списки, рейтинги чи антирейтинги страв. "
            "Завжди використовуй готові таблиці 'gold_*' для аналітики продажів, якщо це можливо."
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Схема бази даних:\n{db_schema}\n\nЗапитання користувача: {user_question}"}
        ]

        response = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=messages,
            temperature=0
        )
        sql_query = response.choices[0].message.content.strip()
        sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
        
        # Захист: перевіряємо, чи це точно SELECT
        if not sql_query.upper().startswith("SELECT"):
            await message.answer("⚠️ Я можу виконувати лише аналітичні запити (тільки пошук та статистика). Зміна чи видалення даних заборонені з міркувань безпеки.")
            await state.clear()
            return

        print(f"🛠 [AI DEBUG] Generated SQL: {sql_query}")
        
        # 2. Виконання запиту з механізмом самовиправлення (Self-Correction)
        conn = get_connection()
        cur = conn.cursor()
        
        rows = None
        error_message = None
        max_retries = 2
        
        for attempt in range(max_retries):
            try:
                cur.execute(sql_query)
                rows = cur.fetchall()
                error_message = None
                break
            except Exception as db_err:
                conn.rollback() # скидаємо транзакцію при помилці
                error_message = str(db_err)
                print(f"⚠️ [AI SQL ERROR] Спроба {attempt+1} не вдалася: {error_message}")
                
                # Просимо модель виправити свій же SQL на основі помилки бази
                fix_response = client.chat.completions.create(
                    model="openai/gpt-oss-20b",
                    messages=[
                        {"role": "system", "content": "Ти відладник SQL. База даних повернула помилку. Виправ SQL-запит і поверни ТІЛЬКИ виправлений чистий SQL без markdown."},
                        {"role": "user", "content": f"Схема:\n{db_schema}\n\nПомилковий SQL:\n{sql_query}\n\nПомилка бази даних:\n{error_message}"}
                    ],
                    temperature=0
                )
                sql_query = fix_response.choices[0].message.content.replace("```sql", "").replace("```", "").strip()
                print(f"🛠 [AI DEBUG] Fixed SQL: {sql_query}")

                if not rows:
                    await message.answer("ℹ️ За вашим запитом не знайдено жодних даних у системі.")
                    await state.clear()
                    return

        cur.close()
        conn.close()

        if error_message:
            await message.answer("❌ Не вдалося сформувати правильний запит до бази даних після кількох спроб.")
            await state.clear()
            return
        
        print(f"📊 [AI DEBUG] DB Result: {rows}")
        
        # 3. Формування фінальної відповіді
        summary_response = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {
                    "role": "system", 
                    "content": "Ти корисний бізнес-асистент ресторану. Напиши коротку, чітку та ввічливу відповідь українською мовою на основі отриманих даних з бази."
                },
                {
                    "role": "user", 
                    "content": f"Запитання: {user_question}\nРезультат виконання SQL з бази даних: {rows}"
                }
            ],
            temperature=0.1
        )
        final_answer = summary_response.choices[0].message.content.strip()
        await message.answer(f"📊 **Результат аналізу:**\n\n{final_answer}", parse_mode="Markdown")
        
    except Exception as e:
        await message.answer(f"❌ Сталася неочікувана помилка під час обробки запиту: {e}")
    
    await state.clear()

# Запуск бота
async def main():
    print("Бот запущений і готовий приймати повідомлення...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())