import os
from playwright.sync_api import sync_playwright

BASE_URL = "https://svoi56.syrve.app"
AUTH_FILE = "auth.json"

def save_user_session():
    print("🔐 Запуск браузера для ручного входу та збереження сесії...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        page.goto(BASE_URL)
        
        print("\n[ІНСТРУКЦІЯ]:")
        print("1. Увійди в систему у відкритому вікні браузера (введи логін/пароль).")
        print("2. Дочекайся завантаження головної сторінки (де плитки меню).")
        input("\nНатисни Enter у цьому терміналі, коли успішно залогінишся...")

        # Зберігаємо куки та стан сесії у файл
        context.storage_state(path=AUTH_FILE)
        print(f"✅ Сесію успішно збережено у файл: {AUTH_FILE}")
        browser.close()

if __name__ == "__main__":
    save_user_session()