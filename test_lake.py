import os
import boto3
from dotenv import load_dotenv

# Завантажуємо змінні середовища
load_dotenv()

# Налаштовуємо підключення до S3-сумісного сховища (Cloudflare R2)
s3_client = boto3.client(
    's3',
    endpoint_url=os.getenv("R2_ENDPOINT_URL"),
    aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
    region_name='auto' 
)

bucket_name = os.getenv("R2_BUCKET_NAME")

# Створюємо тестовий сирий JSON-файл (імітуємо відповідь від iiko API)
test_file_name = "sample_iiko_response.json"
with open(test_file_name, "w", encoding="utf-8") as f:
    f.write('{"restaurant_id": "12345", "status": "success", "data": {"orders": []}}')

try:
    # Завантажуємо файл у хмарний дата-лейк у папку 'raw/'
    s3_client.upload_file(
        Filename=test_file_name,
        Bucket=bucket_name,
        Key=f"raw/test/{test_file_name}"
    )
    print(f"🚀 Успішно! Файл '{test_file_name}' завантажено у хмарний дата-лейк R2!")

except Exception as e:
    print(f"❌ Сталася помилка при завантаженні у дата-лейк: {e}")

# Видаляємо локальний тимчасовий файл
if os.path.exists(test_file_name):
    os.remove(test_file_name)