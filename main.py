import json
import pandas as pd

# 1. Extract (зчитуємо сирі дані з мок-файлу)
with open('mock_iiko_response.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

df = pd.DataFrame(data['transactions'])
print("--- Сирі дані завантажені ---")
print(df)

# 2. Transform (агрегуємо дані: рахуємо загальну виручку по працівниках)
summary = df.groupby('employee')['price'].sum().reset_index()
summary.rename(columns={'price': 'total_sales'}, inplace=True)

print("\n--- Трансформовані дані (виручка по працівниках) ---")
print(summary)