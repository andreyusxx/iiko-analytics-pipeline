import os
import time
import json
import boto3
from datetime import datetime
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()

# Дані для входу та R2
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

def scrape_guest_checks():
    print("Крок 1: Запуск браузера для вивантаження чеків...")
    with sync_playwright() as p:
        # Запускаємо браузер
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        # Переходимо на сторінку входу / кабінету
        print(f"Відкриваємо {BASE_URL}...")
        page.goto(BASE_URL)

        # Тут ми робимо паузу, щоб ти міг залогінитись вручну (або можна прописати автоматичний введення логіна/пароля)
        print("Будь ласка, увійди в систему в відкритому вікні браузера, якщо потрібно, і перейди до розділу 'Деталі за чеками'.")
        input("Натисни Enter у цьому терміналі, коли сторінка з чеками повністю завантажиться у браузері...")

        # Перехоплюємо або витягуємо дані через API-запит, який браузер робить у фоновому режимі
        print("Збираємо дані чеків з активної сесії...")
        
        # Переходимо безпосередньо на сторінку звітів по чеках
        page.goto(f"{BASE_URL}/till-shifts/index.html#/guestcheck")
        time.sleep(5)  # чекаємо прогрузки мережевих запитів

        # Робимо скріншот для перевірки
        page.screenshot(path="checks_debug.png")
        print("Зроблено скріншот стану сторінки: checks_debug.png")

        browser.close()

if __name__ == "__main__":
    scrape_guest_checks()