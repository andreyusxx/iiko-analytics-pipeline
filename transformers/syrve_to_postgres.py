import os
import json
import boto3
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

# Налаштування підключення до Neon та R2
DATABASE_URL = os.getenv("DATABASE_URL")
R2_ENDPOINT = os.getenv("R2_ENDPOINT_URL")
R2_ACCESS_KEY = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET_KEY = os.getenv("R2_SECRET_ACCESS_KEY")
R2_BUCKET = os.getenv("R2_BUCKET_NAME", "iiko-data-lake-raw")

def process_and_load_menu():
    print("Крок 1: Підключення до Cloudflare R2 та пошук найсвіжішого файлу...")
    s3 = boto3.client(
        's3',
        endpoint_url=R2_ENDPOINT,
        aws_access_key_id=R2_ACCESS_KEY,
        aws_secret_access_key=R2_SECRET_KEY
    )
    
    response = s3.list_objects_v2(Bucket=R2_BUCKET, Prefix="syrve/menu/")
    files = response.get('Contents', [])
    
    if not files:
        print("Файлів у бакеті не знайдено!")
        return
        
    # Шукаємо найсвіжіший файл (включно з новими custom_menu)
    latest_file = max(files, key=lambda x: x['LastModified'])['Key']
    print(f"Знайдено найсвіжіший файл: {latest_file}")
    
    print("Крок 2: Завантаження та читання JSON-файлу...")
    obj = s3.get_object(Bucket=R2_BUCKET, Key=latest_file)
    data = json.loads(obj['Body'].read().decode('utf-8'))
    
    print("Крок 3: Перетворення структури API v2 на таблиці...")
    
    # У новій структурі категорії лежать у productCategories та itemCategories
    product_categories = data.get('productCategories', [])
    
    # Збираємо всі категорії та товари з вкладених itemCategories
    all_items = []
    nested_categories = []
    
    # Якщо структура містить itemCategories усередині
    if 'itemCategories' in data:
        for cat in data['itemCategories']:
            cat_id = cat.get("id")
            cat_name = cat.get("name")
            
            nested_categories.append({
                "id": cat_id,
                "name": cat_name,
                "description": cat.get("description", "")
            })
            for item in cat.get("items", []):
                item_id = item.get("id") or item.get("itemId") or item.get("sku")
                
                item_flat = {
                    "id": item_id,
                    "sku": item.get("sku"),
                    "name": item.get("name"),
                    "description": item.get("description", ""),
                    "category_id": cat_id,      # Зберігаємо ID категорії для майбутнього JOIN
                    "category_name": cat_name   # Ім'я залишаємо для зручності читання
                }
                
                # Дістаємо ціну з цінників, якщо вона є
                prices = item.get("prices", [])
                if prices:
                    item_flat["price"] = prices[0].get("price")
                all_items.append(item_flat)

    df_categories = pd.DataFrame(nested_categories)
    df_items = pd.DataFrame(all_items)
    df_categories = pd.DataFrame(nested_categories)
    print(f"Оброблено категорій: {len(df_categories)}. Оброблено товарів: {len(df_items)}.")
    
    print("Крок 4: Підключення до хмарного PostgreSQL (Neon) та запис даних...")
    engine = create_engine(DATABASE_URL)
    
    # Записуємо у Silver шар бази даних
    df_categories.to_sql('syrve_categories', engine, if_exists='replace', index=False)
    df_items.to_sql('syrve_products', engine, if_exists='replace', index=False)
    
    print("Успіх! Усі дані зовнішнього меню успішно завантажені у PostgreSQL (Silver шар).")

if __name__ == "__main__":
    process_and_load_menu()