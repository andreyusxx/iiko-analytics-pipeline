import os
import boto3
from dotenv import load_dotenv
import requests
import json
from datetime import datetime

# Змушуємо Python прочитати твій файл .env
load_dotenv()

# Базова адреса хмарного API Syrve
BASE_URL = "https://api-eu.syrve.live"

# БЕРЕМО САМЕ ДОВГИЙ КЛЮЧ З .env, А НЕ ЛОГІН!
API_KEY = os.getenv("SYRVE_API_KEY")

R2_ENDPOINT = os.getenv("R2_ENDPOINT_URL")
R2_ACCESS_KEY = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET_KEY = os.getenv("R2_SECRET_ACCESS_KEY")
R2_BUCKET = os.getenv("R2_BUCKET_NAME", "iiko-data-lake-raw")

def get_s3_client():
    """Створює клієнт для роботи з Cloudflare R2."""
    return boto3.client(
        's3',
        endpoint_url=R2_ENDPOINT,
        aws_access_key_id=R2_ACCESS_KEY,
        aws_secret_access_key=R2_SECRET_KEY
    )

def fetch_syrve_data_to_bronze():
    """Функція підключається до Syrve API, отримує токен, 
    знаходить ресторан та завантажує сирі дані у Bronze шар."""
    
    print("Крок 1: Авторизація в Syrve API...")
    auth_response = requests.post(
        f"{BASE_URL}/api/1/access_token",
        json={"apiLogin": API_KEY}
    )
    print(f"Статус-код відповіді сервера: {auth_response.status_code}")
    
    if auth_response.status_code != 200:
        raise Exception(f"Помилка авторизації. Статус: {auth_response.status_code}, Текст: {auth_response.text}")
    
        
    token = auth_response.json().get("token")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    print("Крок 2: Отримання списку ресторанів (організацій)...")
    org_response = requests.post(
        f"{BASE_URL}/api/1/organizations",
        headers=headers,
        json={"organizationIds": []}
    )
    
    if org_response.status_code != 200:
        raise Exception(f"Помилка отримання організації: {org_response.text}")
        
    organizations = org_response.json().get("organizations", [])
    if not organizations:
        raise Exception("Не знайдено жодної організації для цього ключа!")
        
    org_id = organizations[0]["id"]
    print(f"Знайдено організацію з ID: {org_id}")
    
    print("Крок 3: Завантаження номенклатури (меню)...")
    menu_response = requests.post(
        f"{BASE_URL}/api/1/nomenclature",
        headers=headers,
        json={"organizationId": org_id}
    )
    
    if menu_response.status_code != 200:
        raise Exception(f"Помилка завантаження меню: {menu_response.text}")
        
    menu_data = menu_response.json()
    
    print("Крок 4: Збереження даних у Bronze шар (Cloudflare R2)...")
    # Генеруємо ім'я файлу з поточною датою та часом
    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"syrve/menu/menu_{current_time}.json"
    
    # Підключаємося до R2 і відправляємо файл
    s3 = get_s3_client()
    s3.put_object(
        Bucket=R2_BUCKET,
        Key=filename,
        Body=json.dumps(menu_data, ensure_ascii=False), # Конвертуємо словник назад у текст
        ContentType="application/json"
    )
    
    print(f"Успіх! Файл збережено у бакет '{R2_BUCKET}' під назвою '{filename}'")
    return "Bronze extraction completed successfully"
if __name__ == "__main__":
    fetch_syrve_data_to_bronze()