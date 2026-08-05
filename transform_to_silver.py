import os
import json
import pandas as pd
import psycopg2
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

def transform_and_load():
    local_file = "mock_sales.json"
    
    if not os.path.exists(local_file):
        print(f"Помилка: Файл {local_file} не знайдено.")
        return

    with open(local_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    df = pd.DataFrame(data)
    print(f"Успішно завантажено {len(df)} записів із файлу для трансформації.")

    try:
        connection = psycopg2.connect(DATABASE_URL)
        cursor = connection.cursor()
        
        # 1. Створюємо таблицю ТІЛЬКИ якщо її ще немає (дані не видаляються!)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS silver_sales (
                order_id VARCHAR(50) PRIMARY KEY,
                datetime TIMESTAMP,
                is_banquet BOOLEAN,
                total_sum NUMERIC(10, 2)
            );
        """)
        connection.commit()

        # 2. Використовуємо UPSERT: якщо запис вже є, оновлюємо його; якщо немає — вставляємо новий
        insert_query = """
            INSERT INTO silver_sales (order_id, datetime, is_banquet, total_sum)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (order_id) DO NOTHING;
        """

        for _, row in df.iterrows():
            cursor.execute(insert_query, (
                row.get("order_id"),
                row.get("datetime"),
                row.get("is_banquet"),
                row.get("total_sum")
            ))
        
        connection.commit()
        print("Дані успішно трансльовані та збережені в таблицю 'silver_sales' у PostgreSQL!")

    except Exception as e:
        print(f"Помилка при роботі з базою даних: {e}")
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

if __name__ == "__main__":
    transform_and_load()