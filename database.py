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
        cur.execute(
            "INSERT INTO staff_shifts (employee_id) VALUES (%s);",
            (employee_id,)
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
            # Якщо немає — додаємо
            cur.execute("INSERT INTO staff_shifts (employee_id) VALUES (%s);", (employee_id,))
            status = "додано"
            
        conn.commit()
        return status
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()