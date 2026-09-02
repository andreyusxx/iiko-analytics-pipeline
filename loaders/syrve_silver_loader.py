import os
import json
import boto3
import psycopg2
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Налаштування R2 та PostgreSQL
R2_ENDPOINT = os.getenv("R2_ENDPOINT_URL")
R2_ACCESS_KEY = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET_KEY = os.getenv("R2_SECRET_ACCESS_KEY")
R2_BUCKET = os.getenv("R2_BUCKET_NAME", "iiko-data-lake-raw")

DATABASE_URL = os.getenv("DATABASE_URL")

def get_s3_client():
    return boto3.client(
        's3',
        endpoint_url=R2_ENDPOINT,
        aws_access_key_id=R2_ACCESS_KEY,
        aws_secret_access_key=R2_SECRET_KEY
    )

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def init_db_tables(conn):
    """Створюємо таблицю трекінгу оброблених файлів та основну Silver-таблицю чеків"""
    with conn.cursor() as cur:
        # Таблиця для відстеження статусів файлів (state tracking)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS processed_files (
                file_name VARCHAR(255) PRIMARY KEY,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Основна Silver-таблиця для очищених даних по чеках/стравах
        cur.execute("""
            CREATE TABLE IF NOT EXISTS silver_guest_checks (
                id SERIAL PRIMARY KEY,
                uniq_order_id VARCHAR(100),
                order_num INT,
                session_num INT,
                table_num INT,
                cashier VARCHAR(100),
                dish_name VARCHAR(255),
                dish_sum NUMERIC(10, 2),
                discount_sum NUMERIC(10, 2),
                open_time TIMESTAMP,
                close_time TIMESTAMP,
                pay_types VARCHAR(255),
                category_name VARCHAR(255),
                source_file VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
    conn.commit()

def process_new_files():
    s3 = get_s3_client()
    conn = get_db_connection()
    init_db_tables(conn)

    print("Крок 1: Отримання списку файлів із Bronze шар R2...")
    response = s3.list_objects_v2(Bucket=R2_BUCKET, Prefix="syrve/guest_checks/")
    
    if "Contents" not in response:
        print("Файлів у сховищі не знайдено.")
        return

    all_r2_files = [obj["Key"] for obj in response["Contents"] if obj["Key"].endswith(".json")]

    if not all_r2_files:
        print("✅ Немає файлів для обробки.")
        return
    # Отримуємо список вже оброблених файлів із бази даних
    with conn.cursor() as cur:
        cur.execute("SELECT file_name FROM processed_files;")
        processed_files = {row[0] for row in cur.fetchall()}

    # Фільтруємо: залишаємо лише ті, яких ще немає в базі
    new_files = [f for f in all_r2_files if f not in processed_files]

    if not new_files:
        print("✅ Усі файли вже оброблені. Нових даних для завантаження немає.")
        return

    print(f"Знайдено нових необоблених файлів: {len(new_files)}")

    for file_key in new_files:
        print(f"Обираємо файл для обробки: {file_key}")
        
        # Читаємо сирий JSON з R2
        obj = s3.get_object(Bucket=R2_BUCKET, Key=file_key)
        raw_content = obj["Body"].read().decode("utf-8")
        data = json.loads(raw_content)

        # Знаходимо масив даних усередині (залежно від структури об'єкта)
        checks_list = []
        if isinstance(data, list):
            checks_list = data
        elif isinstance(data, dict):
            for v in data.values():
                if isinstance(v, list):
                    checks_list = v
                    break

        inserted_count = 0
        with conn.cursor() as cur:
            for item in checks_list:
                cur.execute("DELETE FROM silver_guest_checks WHERE source_file = %s;", (file_key,))
                dish_name = item.get("dishName")

                if dish_name in ("Гарний настрій"):
                    continue

                # Очистка та приведення типів (Silver шар трансформація)
                uniq_order_id = item.get("uniqOrderIdId")
                order_num = item.get("orderNum")
                session_num = item.get("sessionNum")
                table_num = item.get("tableNum")
                cashier = item.get("cashier")
                dish_name = item.get("dishName")
                
                # Числові поля безпечно переводимо в float/numeric
                dish_sum = float(item.get("dishSumInt", 0) or 0)
                discount_sum = float(item.get("discountSum", 0) or 0)
                
                # Безпечний парсинг дат
                open_time_str = item.get("openTime")
                close_time_str = item.get("closeTime")
                
                open_time = datetime.fromisoformat(open_time_str) if open_time_str else None
                close_time = datetime.fromisoformat(close_time_str.split(".")[0]) if close_time_str else None
                
                pay_types = item.get("payTypes")

                # Записуємо очищений рядок у Silver-таблицю
                cur.execute("SELECT category_name FROM syrve_products WHERE name = %s LIMIT 1;", (dish_name,))
                cat_row = cur.fetchone()
                category_name = cat_row[0] if cat_row else None

                cur.execute("""
                    INSERT INTO silver_guest_checks (
                        uniq_order_id, order_num, session_num, table_num, 
                        cashier, dish_name, dish_sum, discount_sum, 
                        open_time, close_time, pay_types, category_name, source_file
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    );
                """, (
                    uniq_order_id, order_num, session_num, table_num,
                    cashier, dish_name, dish_sum, discount_sum,
                    open_time, close_time, pay_types, category_name, file_key
                ))
                inserted_count += 1

            # Фіксуємо факт обробки файлу в таблиці трекінгу
            cur.execute("""
                INSERT INTO processed_files (file_name) VALUES (%s)
                ON CONFLICT (file_name) DO NOTHING;
            """, (file_key,))
            
        conn.commit()
        print(f" Успішно завантажено {inserted_count} записів із файлу {file_key}")

    conn.close()
    print("🚀 Усі нові файли успішно оброблено та перенесено в базу даних!")

if __name__ == "__main__":
    process_new_files()