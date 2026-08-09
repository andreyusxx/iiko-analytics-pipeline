import json
from typing import List
from pydantic import BaseModel, Field, ValidationError

class OrderItemModel(BaseModel):
    dish_id: str
    name: str
    price: float = Field(..., gt=0, description="Ціна страви має бути більшою за нуль")

class OrderModel(BaseModel):
    order_id: str
    datetime: str
    is_banquet: bool
    total_sum: float = Field(..., gt=0, description="Сума чеку має бути більшою за нуль")
    items: List[OrderItemModel]

def validate_raw_json(raw_json_data: str) -> List[dict]:
    """
    Перевіряє сирі JSON-дані перед записом у даталейк.
    Повертає список валідованих словників або викидає помилку валідації.
    """
    try:
        data = json.loads(raw_json_data)
    except json.JSONDecodeError as e:
        raise ValueError(f"Критична помилка: файл не є валідним JSON -> {e}")

    # Якщо прийшов один об'єкт, загортаємо у список для універсальності
    if isinstance(data, dict):
        data = [data]
    elif not isinstance(data, list):
        raise TypeError("Дані мають бути об'єктом або списком об'єктів JSON.")

    validated_records = []
    
    for index, record in enumerate(data):
        try:
            # Pydantic автоматично звіряє типи та правила (наприклад, gt=0)
            valid_order = OrderModel(**record)
            validated_records.append(valid_order.model_dump())
        except ValidationError as e:
            order_id = record.get('order_id', 'невідомо')
            raise ValueError(f"Помилка якості даних у записі #{index} (order_id: {order_id}):\n{e}")

    print("Успішно: усі сирі дані пройшли перевірку схеми та готові до завантаження в R2.")
    return validated_records

# Приклад тестування функції:
if __name__ == "__main__":
    sample_json = '''
    [
        {
            "order_id": "ord_90832",
            "datetime": "2026-08-09 12:00:00",
            "is_banquet": false,
            "total_sum": 1050.00,
            "items": [
                {"dish_id": "item_1", "name": "Стейк з лосося", "price": 450.00},
                {"dish_id": "item_3", "name": "Вино Шато", "price": 600.00}
            ]
        }
    ]
    '''
    validated_data = validate_raw_json(sample_json)