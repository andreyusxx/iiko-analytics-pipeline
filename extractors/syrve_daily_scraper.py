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

SYRVE_LOGIN = os.getenv("SYRVE_LOGIN")
SYRVE_PASSWORD = os.getenv("SYRVE_PASSWORD")
AUTH_FILE = "auth.json"

def extract_today_checks():
    target_date = datetime.now().strftime("%Y-%m-%d")
    print(f"-> Автоматичний збір даних за поточний день: {target_date}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        if os.path.exists(AUTH_FILE):
            print("🔑 Використовуємо збережену сесію (auth.json)...")
            context = browser.new_context(storage_state=AUTH_FILE)
        else:
            print("⚠️ Файл сесії не знайдено. Буде потрібен ручний вхід або створення сесії.")
            context = browser.new_context()

        page = context.new_page()

        captured_json_data = None

        def handle_response(response):
            nonlocal captured_json_data
            if "api/report/guestcheck" in response.url:
                try:
                    if response.status == 200:
                        data = response.json()
                        if data:
                            captured_json_data = data
                except Exception:
                    pass

        page.on("response", handle_response)

        try:
            print("Переходимо на сторінку 'Деталі за чеками'...")
            # Завдяки auth.json ми відразу потрапимо на сторінку звітів в обхід форми логіну
            page.goto(f"{BASE_URL}/till-shifts/index.html#/guestcheck", timeout=60000)

            print("Очікування завантаження даних за сьогодні...")
            page.wait_for_timeout(15000)
            

        except Exception as err:
            print(f"❌ Помилка під час автоматизації: {err}")
        finally:
            browser.close()

        if not captured_json_data:
            raise Exception("❌ Не вдалося автоматично перехопити дані за сьогодні!")

        # 4. Зберігаємо у R2
        filename = f"syrve/guest_checks/guestchecks_{target_date.replace('-', '')}.json"
        
        print(f"📤 Завантаження файлу в R2 -> {filename}")
        s3 = boto3.client(
            's3',
            endpoint_url=R2_ENDPOINT,
            aws_access_key_id=R2_ACCESS_KEY,
            aws_secret_access_key=R2_SECRET_KEY
        )
        s3.put_object(
            Bucket=R2_BUCKET,
            Key=filename,
            Body=json.dumps(captured_json_data, ensure_ascii=False, indent=2),
            ContentType="application/json"
        )
        print("🚀 Успіх! Дані за сьогодні успішно збережено в сховище R2.")

if __name__ == "__main__":
    extract_today_checks()