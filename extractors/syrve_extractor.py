import os
from dotenv import load_dotenv
import requests
import json

# Змушуємо Python прочитати твій файл .env
load_dotenv()

# Базова адреса хмарного API Syrve
BASE_URL = "https://api-eu.syrve.live"

# БЕРЕМО САМЕ ДОВГИЙ КЛЮЧ З .env, А НЕ ЛОГІН!
API_KEY = os.getenv("SYRVE_API_KEY")

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
    
    # Тут у майбутньому ми збережемо menu_data у Cloudflare R2 (Bronze шар)
    print(f"Успішно завантажено меню. Кількість категорій/товарів: {len(menu_data.get('groups', []))}")
    
    # Повертаємо успішний статус або зберігаємо файли
    return "Bronze extraction completed successfully"

if __name__ == "__main__":
    fetch_syrve_data_to_bronze()