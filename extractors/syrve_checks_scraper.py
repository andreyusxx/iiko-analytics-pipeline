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
def get_s3_client():
    return boto3.client(
        's3',
        endpoint_url=R2_ENDPOINT,
        aws_access_key_id=R2_ACCESS_KEY,
        aws_secret_access_key=R2_SECRET_KEY
    )

def intercept_checks_by_date(target_date: str = None):
    if not target_date:
        target_date = datetime.now().strftime("%Y-%m-%d")
        
    print(f"-> Повністю автоматичний збір даних для дати: {target_date}")

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

        try:
            print(f"Відкриваємо {BASE_URL}...")
            page.goto(BASE_URL, timeout=60000)

            # --- АВТОМАТИЧНИЙ ВХІД (Замість ручного клікання) ---
            # Увага: селектори (input[name='login'] тощо) треба буде підігнати під реальні поля твого сайту Syrve
            print("Виконуємо автоавторизацію...")
            page.fill("input[name='login']", SYRVE_LOGIN) # Селектор поля логіна
            page.fill("input[name='password']", SYRVE_PASSWORD) # Селектор поля пароля
            page.click("button[type='submit']") # Кнопка входу
            
            # Чекаємо завантаження головної сторінки
            page.wait_for_load_timeout(5000)

            page.goto(f"{BASE_URL}/till-shifts/index.html#/guestcheck", timeout=60000)

            page.wait_for_selector("input, .date-picker, app-date-picker", timeout=15000)

            print(f"Чекаємо на формування звіту за дату {target_date}...")
            # Робимо паузу на завантаження мережевого запиту
            page.wait_for_timeout(10000)

        except Exception as err:
            print(f"❌ Помилка під час автоматизації браузера: {err}")
        finally:
            browser.close()

        if not captured_json_data:
            print("❌ Попередження: Не вдалося зловити JSON-дані звітів автоматично.")
            return
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