import json
import random
from datetime import datetime, timedelta

def generate_mock_sales():
    """Генерує список мокових чеків (продажів) ресторану, включаючи банкетні замовлення."""
    menu_items = [
        {"id": "item_1", "name": "Стейк з лосося", "price": 450, "category": "Основні страви"},
        {"id": "item_2", "name": "Цезар з куркою", "price": 220, "category": "Салати"},
        {"id": "item_3", "name": "Вино Шато", "price": 600, "category": "Алкоголь"},
        {"id": "item_4", "name": "Десерт Тірамісу", "price": 180, "category": "Десерти"}
    ]
    
    orders = []
    start_date = datetime.now() - timedelta(days=7) # Дані за останній тиждень
    
    for i in range(50): # Генеруємо 50 тестових чеків
        order_id = f"ord_{1000 + i}"
        is_banquet = random.choice([True, False]) # Випадково визначаємо, чи це банкет
        order_time = start_date + timedelta(hours=random.randint(0, 168))
        
        items_in_order = []
        total_sum = 0
        
        # Додаємо від 1 до 4 страв у чек (для банкетів робимо суму більшою)
        num_items = random.randint(3, 8) if is_banquet else random.randint(1, 3)
        for _ in range(num_items):
            dish = random.choice(menu_items)
            quantity = random.randint(1, 4) if is_banquet else 1
            items_in_order.append({
                "dish_id": dish["id"],
                "name": dish["name"],
                "price": dish["price"],
                "quantity": quantity
            })
            total_sum += dish["price"] * quantity

        orders.append({
            "order_id": order_id,
            "datetime": order_time.strftime("%Y-%m-%d %H:%M:%S"),
            "is_banquet": is_banquet,
            "total_sum": total_sum,
            "items": items_in_order
        })
        
    return orders

if __name__ == "__main__":
    data = generate_mock_sales()
    # Зберігаємо згенеровані дані у локальний JSON-файл (імітація сирих даних)
    with open("mock_sales.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print("Успішно згенеровано 50 мокових чеків у файл mock_sales.json!")