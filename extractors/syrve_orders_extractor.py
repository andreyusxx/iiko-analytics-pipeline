import os
import boto3
from dotenv import load_dotenv
import requests
import json
from datetime import datetime, timedelta

load_dotenv()

BASE_URL = "https://api-eu.syrve.live"
API_KEY = os.getenv("SYRVE_API_KEY")

R2_ENDPOINT = os.getenv("R2_ENDPOINT_URL")
R2_ACCESS_KEY = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET_KEY = os.getenv("R2_SECRET_ACCESS_KEY")
R2_BUCKET = os.getenv("R2_BUCKET_NAME", "iiko-data-lake-raw")

def get_s3_client():
    return boto3.client(
        's3',
        endpoint_url=R2_ENDPOINT,
        aws_access_key_id=R2_ACCESS_KEY,
        aws_secret_access_key=R2_SECRET_KEY
    )

def fetch_orders_to_bronze():
    print("Крок 1: Авторизація в Syrve API...")
    auth_response = requests.post(
        f"{BASE_URL}/api/1/access_token",
        json={"apiLogin": API_KEY}
    )
    
    if auth_response.status_code != 200:
        raise Exception(f"Помилка авторизації: {auth_response.text}")
        
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
    
    # Визначаємо період за останню добу
    date_to = datetime.now()
    date_from = date_to - timedelta(days=1)
    
    date_from_str = date_from.strftime("%Y-%m-%d %H:%M:%S")
    date_to_str = date_to.strftime("%Y-%m-%d %H:%M:%S")
    
    print(f"Крок 3: Завантаження замовлень з {date_from_str} по {date_to_str}...")
    
    # Використовуємо офіційний метод для замовлень з правильним новим токеном
    orders_resp = requests.post(
        f"{BASE_URL}/api/1/deliveries/by_filter",
        headers=headers,
        json={
            "organizationIds": [org_id],
            "returnCancelled": True,
            "dateFrom": date_from_str,
            "dateTo": date_to_str
        }
    )
    
    print(f"Статус-код запиту замовлень: {orders_resp.status_code}")
    
    if orders_resp.status_code != 200:
        print(f"Помилка API замовлень: {orders_resp.text}")
        return
        
    orders_data = orders_resp.json()
    
    filename = f"syrve/orders/orders_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    print(f"Крок 4: Збереження замовлень в R2 -> {filename}")
    
    s3 = get_s3_client()
    s3.put_object(
        Bucket=R2_BUCKET,
        Key=filename,
        Body=json.dumps(orders_data, ensure_ascii=False),
        ContentType="application/json"
    )
    print("Успіх! Замовлення успішно збережено у R2.")

if __name__ == "__main__":
    fetch_orders_to_bronze()