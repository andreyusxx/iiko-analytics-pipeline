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