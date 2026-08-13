import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

# Отримуємо рядок підключення до Neon з .env
DATABASE_URL = os.getenv("DATABASE_URL")

def get_connection():
    """Створює та повертає підключення до бази даних Neon"""
    return psycopg2.connect(DATABASE_URL)

def add_employee(full_name: str, role: str, daily_rate: float):
    """Додає нового працівника до довідника"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO employees (full_name, role, daily_rate) VALUES (%s, %s, %s);",
            (full_name, role, daily_rate)
        )
        conn.commit()
        print(f"Працівника {full_name} успішно додано!")
    except Exception as e:
        conn.rollback()
        print(f"Помилка при додаванні працівника: {e}")
    finally:
        cur.close()
        conn.close()

def register_shift(employee_id: int):
    """Фіксує вихід працівника на зміну сьогодні"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        # Спочатку отримуємо поточну ставку працівника
        cur.execute("SELECT daily_rate FROM employees WHERE id = %s;", (employee_id,))
        emp_row = cur.fetchone()
        if not emp_row:
            raise ValueError("Працівника не знайдено")
        current_rate = emp_row[0]
        cur.execute(
            "INSERT INTO staff_shifts (employee_id, shift_rate) VALUES (%s, %s);",
            (employee_id, current_rate)
        )
        conn.commit()
        print(f"Зміну для працівника з ID {employee_id} успішно зареєстровано!")
    except Exception as e:
        conn.rollback()
        print(f"Помилка при реєстрації зміни: {e}")
    finally:
        cur.close()
        conn.close()

def update_employee(employee_id: int, full_name: str, role: str, daily_rate: float):
    """Оновлює дані працівника за його ID"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE employees SET full_name = %s, role = %s, daily_rate = %s WHERE id = %s;",
            (full_name, role, daily_rate, employee_id)
        )
        # Перевіряємо, чи був оновлений хоча б один рядок
        if cur.rowcount == 0:
            raise ValueError(f"Працівника з ID {employee_id} не знайдено.")
            
        conn.commit()
    except Exception as e:
        conn.rollback()
        # Прокидаємо помилку далі, щоб бот знав про неї
        raise e
    finally:
        cur.close()
        conn.close()

def toggle_shift(employee_id: int):
    """Додає або видаляє зміну для працівника на сьогодні"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        # Перевіряємо, чи є вже запис на сьогодні
        cur.execute(
            "SELECT id FROM staff_shifts WHERE employee_id = %s AND shift_date = CURRENT_DATE;",
            (employee_id,)
        )
        exists = cur.fetchone()
        
        if exists:
            # Якщо є — видаляємо (скасовуємо вихід)
            cur.execute("DELETE FROM staff_shifts WHERE id = %s;", (exists[0],))
            status = "видалено"
        else:
            # Отримуємо поточну ставку працівника на момент виходу
            cur.execute("SELECT daily_rate FROM employees WHERE id = %s;", (employee_id,))
            emp_row = cur.fetchone()
            if not emp_row:
                raise ValueError("Працівника не знайдено")
            current_rate = emp_row[0]

            # Якщо немає — додаємо
            cur.execute("INSERT INTO staff_shifts (employee_id, shift_rate) VALUES (%s, %s);", (employee_id, current_rate))
            status = "додано"
            
        conn.commit()
        return status
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()

def get_unpaid_shifts():
    """Повертає список боргів по змінах"""
    conn = get_connection()
    cur = conn.cursor()
    # Групуємо по працівнику, щоб бачити, скільки кожен відпрацював неоплачених днів
    cur.execute("""
        SELECT e.full_name, COUNT(s.id) as days_worked, SUM(s.shift_rate) as total_debt
        FROM staff_shifts s
        JOIN employees e ON s.employee_id = e.id
        WHERE s.is_paid = FALSE
        GROUP BY e.full_name;
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def mark_all_unpaid_as_paid(start_date, end_date):
    """Позначає зміни у вказаному діапазоні як оплачені"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE staff_shifts 
            SET is_paid = TRUE 
            WHERE shift_date BETWEEN %s AND %s;
        """, (start_date, end_date))
        conn.commit()
        count = cur.rowcount
        cur.close()
        conn.close()
        return count
    except Exception as e:
        conn.rollback()
        raise e
    
def get_today_shifts():
    """Повертає список працівників, які мають зміну сьогодні"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT e.full_name, e.role 
        FROM staff_shifts s
        JOIN employees e ON s.employee_id = e.id
        WHERE s.shift_date = CURRENT_DATE;
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows