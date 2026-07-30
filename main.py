import os
from dotenv import load_dotenv
import pandas as pd
from sqlalchemy import create_engine

# Завантажуємо змінні середовища з файлу .env
load_dotenv()

# Отримуємо рядок підключення до бази даних
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("❌ Помилка: DATABASE_URL не знайдено у файлі .env!")
else:
    print("✅ Рядок підключення успішно завантажено!")

    try:
        # Створюємо підключення (Engine) до PostgreSQL
        engine = create_engine(DATABASE_URL)

        # Робимо тестовий запит до бази даних через pandas
        test_df = pd.read_sql("SELECT version();", engine)
        
        print("\n🚀 Успішне з'єднання з базою даних Neon!")
        print("Версія бази даних PostgreSQL:")
        print(test_df.iloc[0, 0])

    except Exception as e:
        print(f"❌ Сталася помилка при підключенні до бази даних: {e}")