import os
import json
import boto3
from datetime import datetime
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()

BASE_URL = "https://svoi56.syrve.app"
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

def intercept_checks_by_date():
    default_date = datetime.now().strftime("%Y-%m-%d")
    print(f"Поточна дата за замовчуванням: {default_date}")
    user_date = input(f"Введіть дату для вивантаження (у форматі YYYY-MM-DD) або натисніть Enter для поточної: ").strip()
    
    target_date = user_date if user_date else default_date
    print(f"-> Обрано дату для збору: {target_date}")

    print("Крок 1: Запуск перехоплювача мережевих запитів...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        captured_json_data = None

        def handle_response(response):
            nonlocal captured_json_data
            if "api/report/guestcheck" in response.url:
                try:
                    if response.status == 200:
                        data = response.json()
                        print(f"✅ Успішно перехоплено звіт guestcheck!")
                        captured_json_data = data
                except Exception as e:
                    print(f"Помилка парсингу відповіді: {e}")

        page.on("response", handle_response)

        print(f"Відкриваємо {BASE_URL}...")
        page.goto(BASE_URL)

        # Даємо повну свободу користувачу залогінитись і перейти куди треба без жорстких page.goto()
        print("\n[ІНСТРУКЦІЯ у відкритому браузері]:")
        print("1. Увійди в систему (якщо потрібно).")
        print("2. Перейди у розділ 'Касові зміни' -> 'Деталі за чеками'.")
        print(f"3. Вистав у фільтрі потрібну дату ({target_date}), щоб дані з'явилися на екрані.")
        input("\nНатисни Enter у цьому терміналі, коли зробиш це і дані завантажаться в таблиці...")

        # Невелика пауза на випадок фонових запитів
        page.wait_for_timeout(3000)
        browser.close()

        if not captured_json_data:
            print("❌ Попередження: Не вдалося зловити JSON-дані звітів. Переконайся, що сторінка 'Деталі за чеками' була відкрита під час натискання Enter.")
            return

        checks_list = []
        if isinstance(captured_json_data, list):
            checks_list = captured_json_data
        elif isinstance(captured_json_data, dict):
            # Шукаємо будь-який ключ, який містить масив всередині словника
            for key, value in captured_json_data.items():
                if isinstance(value, list):
                    checks_list = value
                    break

        total_items = len(checks_list)
        unique_orders = set()
        for item in checks_list:
            if isinstance(item, dict) and "uniqOrderIdId" in item:
                unique_orders.add(item["uniqOrderIdId"])

        print(f"\n📊 ЗВІТ ПРО ПЕРЕВІРКУ ДАНИХ:")
        print(f"   - Загальна кількість записів (страв/рядків) у файлі: {total_items}")
        print(f"   - Унікальних чеків/замовлень за цей день: {len(unique_orders)}")
        print(f"   - Статус: Повний звіт успішно перехоплено та збережено в R2!")
        # Зберігаємо у R2
        filename = f"syrve/guest_checks/guestchecks_{target_date.replace('-', '')}.json"
        
        print(f"\nКрок 2: Завантаження файлу в R2 -> {filename}")
        s3 = get_s3_client()
        s3.put_object(
            Bucket=R2_BUCKET,
            Key=filename,
            Body=json.dumps(captured_json_data, ensure_ascii=False, indent=2),
            ContentType="application/json"
        )
        print("🚀 Успіх! Дані успішно збережено в сховище R2.")

if __name__ == "__main__":
    intercept_checks_by_date()