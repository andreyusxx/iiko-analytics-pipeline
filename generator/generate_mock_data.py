import os
import json
import random
from datetime import datetime, timedelta
import boto3
from botocore.client import Config
from dotenv import load_dotenv

load_dotenv()

from validator import validate_raw_json

R2_ENDPOINT_URL = os.getenv("R2_ENDPOINT_URL")
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY")
BUCKET_NAME = "iiko-data-lake-raw"

def generate_and_upload_sales():
    """Генерує список мокових чеків (продажів) ресторану, включаючи банкетні замовлення."""
    menu_items = [
        {"id": "item_1", "name": "Стейк з лосося", "price": 450, "category": "Основні страви"},
        {"id": "item_2", "name": "Цезар з куркою", "price": 220, "category": "Салати"},
        {"id": "item_3", "name": "Вино Шато", "price": 600, "category": "Алкоголь"},
        {"id": "item_4", "name": "Десерт Тірамісу", "price": 180, "category": "Десерти"}
    ]
    
    orders = []
    start_date = datetime.now() - timedelta(days=7) # Дані за останній тиждень
    
    for i in range(50): # Генеруємо 50 тестових чеків
        order_id = f"ord_{random.randint(10000, 99999)}"
        is_banquet = random.choice([True, False]) # Випадково визначаємо, чи це банкет
        order_time = start_date + timedelta(hours=random.randint(0, 168))
        
        items_in_order = []
        total_sum = 0
        
        # Додаємо від 1 до 4 страв у чек (для банкетів робимо суму більшою)
        num_items = random.randint(3, 8) if is_banquet else random.randint(1, 3)
        for _ in range(num_items):
            dish = random.choice(menu_items)
            quantity = random.randint(1, 4) if is_banquet else 1
            items_in_order.append({
                "dish_id": dish["id"],
                "name": dish["name"],
                "price": dish["price"],
                "quantity": quantity
            })
            total_sum += dish["price"] * quantity

        orders.append({
            "order_id": order_id,
            "datetime": order_time.strftime("%Y-%m-%d %H:%M:%S"),
            "is_banquet": is_banquet,
            "total_sum": total_sum,
            "items": items_in_order
        })
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"sales_batch_{timestamp_str}.json"
    
    json_data = json.dumps(orders, ensure_ascii=False, indent=4)

    try:
        print("Починаємо валідацію сирих JSON-даних...")
        validate_raw_json(json_data)
        print("Валідація успішна! Дані чисті, продовжуємо завантаження.")
    except Exception as e:
        print(f"ПОМИЛКА ЯКОСТІ ДАНИХ! Завантаження в даталейк скасовано.")
        # Викидаємо виняток, щоб Airflow позначив таску як Failed
        raise ValueError(f"Зупинка пайплайну: {e}")
    
    s3_client = boto3.client(
            's3',
            endpoint_url=R2_ENDPOINT_URL,
            aws_access_key_id=R2_ACCESS_KEY_ID,
            aws_secret_access_key=R2_SECRET_ACCESS_KEY,
            config=Config(signature_version='s3v4')
        )
            
    cloud_path = f"bronze/sales/{filename}"
            
    try:
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=cloud_path,
            Body=json_data,
            ContentType="application/json"
        )
        print(f"Успішно згенеровано та завантажено новий унікальний файл: {cloud_path}")
    except Exception as e:
        print(f"Помилка при завантаженні в R2: {e}")

if __name__ == "__main__":
    generate_and_upload_sales()