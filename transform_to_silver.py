import os
import json
import boto3
import pandas as pd
import psycopg2
from dotenv import load_dotenv

# Завантажуємо змінні середовища з файлу .env
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
R2_ENDPOINT_URL = os.getenv("R2_ENDPOINT_URL")
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME")

def run_incremental_etl():
    # Ініціалізуємо S3-клієнт для роботи з Cloudflare R2
    s3_client = boto3.client(
        "s3",
        endpoint_url=R2_ENDPOINT_URL,
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        region_name="auto"
    )
    
    connection = None
    cursor = None
    
    try:
        # Підключаємося до бази даних PostgreSQL
        connection = psycopg2.connect(DATABASE_URL)
        cursor = connection.cursor()
        
        # 1. Створюємо таблицю для даних (Silver) та таблицю для збереження стану (State Table)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS silver_sales (
                order_id VARCHAR(50) PRIMARY KEY,
                datetime TIMESTAMP,
                is_banquet BOOLEAN,
                total_sum NUMERIC(10, 2)
            );

            CREATE TABLE IF NOT EXISTS silver_sale_items (
                id SERIAL PRIMARY KEY,
                order_id VARCHAR(50) REFERENCES silver_sales(order_id),
                dish_id VARCHAR(50),
                name VARCHAR(100),
                price NUMERIC(10, 2),
                quantity INT
            );
            
            CREATE TABLE IF NOT EXISTS processed_files (
                file_name VARCHAR(255) PRIMARY KEY,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        connection.commit()
        
        # 2. Отримуємо список файлів, які вже були оброблені раніше
        cursor.execute("SELECT file_name FROM processed_files;")
        processed_files_set = {row[0] for row in cursor.fetchall()}
        
        # 3. Отримуємо список усіх файлів з хмарного дата-лейку (R2)
        response = s3_client.list_objects_v2(
            Bucket=R2_BUCKET_NAME, 
            Prefix="bronze/sales/"
        )
        
        if "Contents" not in response:
            print("Дата-лейк R2 наразі порожній. Немає файлів для обробки.")
            return

        all_files = response["Contents"]
        # Сортуємо файли за часом створення (хронологічно: від старих до нових)
        all_files_sorted = sorted(all_files, key=lambda x: x["LastModified"])
        
        # 4. Фільтруємо: залишаємо лише ті файли, яких ще немає в базі станів
        new_files = [f for f in all_files_sorted if f["Key"] not in processed_files_set]
        
        if not new_files:
            print("Нових файлів у дата-лейку немає. Усі дані вже актуальні.")
            return

        print(f"Знайдено нових файлів для обробки: {len(new_files)}")

        # Підготовка SQL-запитів
        insert_sales_query = """
            INSERT INTO silver_sales (order_id, datetime, is_banquet, total_sum)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (order_id) DO NOTHING;
        """
        
        insert_state_query = """
            INSERT INTO processed_files (file_name)
            VALUES (%s)
            ON CONFLICT (file_name) DO NOTHING;
        """

        insert_item_query = """
            INSERT INTO silver_sale_items (order_id, dish_id, name, price, quantity)
            VALUES (%s, %s, %s, %s, %s);
        """

        # 5. Цикл обробки виключно нових файлів
        for file_info in new_files:
            file_key = file_info["Key"]
            print(f"Починаємо обробку нового файлу: {file_key}")
            
            # Завантажуємо вміст файлу з R2
            file_obj = s3_client.get_object(Bucket=R2_BUCKET_NAME, Key=file_key)
            file_content = file_obj["Body"].read().decode("utf-8")
            data = json.loads(file_content)
            
            # Перетворюємо у DataFrame (безпечно обробляємо і список, і одиночний об'єкт)
            df = pd.DataFrame(data if isinstance(data, list) else [data])

            success_rows = 0
            # Записуємо рядки в основну таблицю silver_sales
            for _, row in df.iterrows():
                order_id = row.get("order_id")

                if not order_id:
                    print(111)  # Залишено для відладки, якщо потрібно бачити пропущені рядки
                    continue

                cursor.execute(insert_sales_query, (
                    order_id,
                    row.get("datetime"),
                    row.get("is_banquet"),
                    row.get("total_sum")
                ))

                items = row.get("items", [])
                for item in items:
                    cursor.execute(insert_item_query, (
                        order_id,
                        item.get("dish_id"),
                        item.get("name"),
                        item.get("price"),
                        item.get("quantity")
                    ))
                success_rows += 1
            # Фіксуємо факт успішної обробки файлу в таблиці станів
            cursor.execute(insert_state_query, (file_key,))
            connection.commit()
            print(f"Файл {file_key} успішно оброблено (записано рядків: {success_rows}).")

        print("Інкрементальне завантаження успішно завершено!")

    except Exception as e:
        if connection:
            connection.rollback()  # Відкочуємо транзакцію у разі помилки
        print(f"Помилка під час виконання ETL-пайплайну: {e}")
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

if __name__ == "__main__":
    run_incremental_etl()