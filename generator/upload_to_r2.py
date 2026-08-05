import os
import boto3
from botocore.client import Config
from dotenv import load_dotenv

# Завантажуємо змінні середовища з файлу .env
load_dotenv()

R2_ENDPOINT_URL = os.getenv("R2_ENDPOINT_URL")
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY")
BUCKET_NAME = "iiko-data-lake-raw"  # Назва твого бакету в R2

def upload_mock_data():
    """Завантажує локальний файл mock_sales.json у хмарний дата-лейк (шпарину Bronze)."""
    # Ініціалізуємо S3-клієнт для роботи з Cloudflare R2
    s3_client = boto3.client(
        's3',
        endpoint_url=R2_ENDPOINT_URL,
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        config=Config(signature_version='s3v4')
    )
    
    local_file = "mock_sales.json"
    # Шлях у дата-лейку: структура папок у хмарі (шар Bronze)
    cloud_path = "bronze/sales/mock_sales.json"
    
    try:
        s3_client.upload_file(local_file, BUCKET_NAME, cloud_path)
        print(f"Успішно! Файл {local_file} завантажено в R2 бакет '{BUCKET_NAME}' за шляхом '{cloud_path}'.")
    except Exception as e:
        print(f"Сталася помилка при завантаженні: {e}")

if __name__ == "__main__":
    upload_mock_data()