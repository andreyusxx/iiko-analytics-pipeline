import os
import json
import boto3
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

# Завантажуємо змінні з .env
load_dotenv()

# Налаштування Cloudflare R2
R2_ENDPOINT = os.getenv("R2_ENDPOINT_URL")
R2_ACCESS_KEY = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET_KEY = os.getenv("R2_SECRET_ACCESS_KEY")
R2_BUCKET = os.getenv("R2_BUCKET_NAME", "iiko-data-lake-raw")

# Беремо готове посилання на хмарну базу Neon
DATABASE_URL = os.getenv("DATABASE_URL")

def get_s3_client():
    """Створюємо клієнт для підключення до бакета."""
    return boto3.client(
        's3',
        endpoint_url=R2_ENDPOINT,
        aws_access_key_id=R2_ACCESS_KEY,
        aws_secret_access_key=R2_SECRET_KEY
    )

def process_and_load_menu():
    print("Крок 1: Підключення до Cloudflare R2 та пошук найсвіжішого файлу...")
    s3 = get_s3_client()
    
    response = s3.list_objects_v2(Bucket=R2_BUCKET, Prefix="syrve/menu/")
    if 'Contents' not in response:
        raise Exception("У бакеті немає жодного файлу з меню!")
        
    all_files = response['Contents']
    latest_file = sorted(all_files, key=lambda x: x['LastModified'])[-1]
    file_key = latest_file['Key']
    print(f"Знайдено найсвіжіший файл: {file_key}")
    
    print("Крок 2: Завантаження та читання JSON-файлу...")
    file_obj = s3.get_object(Bucket=R2_BUCKET, Key=file_key)
    file_content = file_obj['Body'].read().decode('utf-8')
    menu_data = json.loads(file_content)
    
    print("Крок 3: Перетворення JSON на плоскі таблиці (Pandas)...")
    df_groups = pd.DataFrame(menu_data.get('groups', []))
    df_products = pd.DataFrame(menu_data.get('products', []))
    print(f"Оброблено категорій: {len(df_groups)}. Оброблено товарів: {len(df_products)}.")
    categories_cols = ['id', 'name', 'parentGroup', 'isIncludedInMenu', 'isDeleted']
    df_groups = df_groups[categories_cols]
    
    products_cols = ['id', 'name', 'groupId', 'code', 'type', 'weight', 'measureUnit', 'sizePrices', 'isDeleted']
    df_products = df_products[products_cols]
    # ----------------------------------------------------
    
    print(f"Оброблено категорій: {len(df_groups)}. Оброблено товарів: {len(df_products)}.")
    
    print("Крок 3.2: Перетворення вкладених списків та словників на текст...")
    def serialize_complex_types(df):
        for col in df.columns:
            df[col] = df[col].apply(
                lambda x: json.dumps(x, ensure_ascii=False) if isinstance(x, (dict, list)) else x
            )
        return df

    df_groups = serialize_complex_types(df_groups)
    df_products = serialize_complex_types(df_products)
    
    print("Крок 4: Підключення до хмарного PostgreSQL (Neon) та запис даних...")
    engine = create_engine(DATABASE_URL)
    
    df_groups.to_sql('syrve_categories', engine, if_exists='replace', index=False)
    df_products.to_sql('syrve_products', engine, if_exists='replace', index=False)
    
    print("Успіх! Усі дані успішно завантажені у PostgreSQL (Silver шар).")


if __name__ == "__main__":
    process_and_load_menu()