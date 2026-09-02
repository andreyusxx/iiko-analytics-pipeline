from datetime import datetime, timedelta
# Імпортуємо твою функцію зкрапера
from extractors.syrve_checks_scraper import intercept_checks_by_date
# Імпортуємо silver-лоадер, щоб одразу перенести дані в базу та оновити вітрини
from loaders.syrve_silver_loader import process_new_files
from transformers.create_gold_layer import build_gold_layer

if __name__ == "__main__":
    # Рахуємо дату за вчора
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    print(f"🧪 Тестовий запуск збору даних за ВЧОРА: {yesterday}")
    
    # 1. Запускаємо вивантаження чеків за вчора в Bronze шар (R2)
    intercept_checks_by_date(target_date=yesterday)
    
    # 2. Очищуємо та переносимо дані в Silver шар (Neon DB)
    print("\n🔄 Запуск Silver-трансформації...")
    process_new_files()
    
    # 3. Оновлюємо Gold-шар (вітрини для аналітики та бота)
    print("\n📊 Оновлення Gold-шару (вітрин)...")
    build_gold_layer()
    
    print("\n✨ Тест успішно завершено! Дані за вчора завантажено, оброблено та готові до аналізу.")