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
EXTERNAL_MENU_ID = "10963"
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
    
    print("Крок 2: Отримання ID ресторану...")
    org_response = requests.post(f"{BASE_URL}/api/1/organizations", headers=headers, json={"organizationIds": []})
    orgs = org_response.json().get("organizations", [])
    
    if not orgs:
        print("Організацій не знайдено!")
        return

    org_id = orgs[0]["id"]
    print(f" -> Знайдено ресторан ID: {org_id}")
    
    print(f"Крок 3: Завантаження зовнішнього меню (ID: {EXTERNAL_MENU_ID}) через API v2...")
    
    menu_resp = requests.post(
        f"{BASE_URL}/api/2/menu/by_id",
        headers=headers,
        json={
            "externalMenuId": EXTERNAL_MENU_ID,
            "organizationIds": [org_id]
        }
    )
    
    print(f"Статус-код запиту меню: {menu_resp.status_code}")
    
    if menu_resp.status_code != 200:
        print(f"Помилка API: {menu_resp.text}")
        return
        
    menu_data = menu_resp.json()
    
    filename = f"syrve/menu/custom_menu_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    print(f"Крок 4: Збереження сирого файлу зовнішнього меню в R2...")
    
    s3 = get_s3_client()
    s3.put_object(
        Bucket=R2_BUCKET,
        Key=filename,
        Body=json.dumps(menu_data, ensure_ascii=False),
        ContentType="application/json"
    )
    print(f"Успіх! Файл збережено: '{filename}'")
    
if __name__ == "__main__":
    fetch_syrve_data_to_bronze()