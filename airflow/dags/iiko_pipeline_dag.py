import sys
import os
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.exceptions import AirflowException
# Додаємо шлях до нашого проєкту в системний шлях Python всередині контейнера
sys.path.insert(0, '/opt/airflow/project')

# Імпортуємо твої наявні функції
from generator.generate_mock_data import generate_and_upload_sales
from transform_to_silver import run_incremental_etl
from create_gold_layer import create_gold_views

default_args = {
    'owner': 'andrii',
    'depends_on_past': False,
    'email_on_failure': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}
def check_data_quality():
    # Підключаємося до бази Neon через налаштоване з'єднання в Airflow
    hook = PostgresHook(postgres_conn_id='postgres_default')
    
    # Перевірка 1: Чи є від'ємні або нульові чеки
    records_negative = hook.get_first(
        "SELECT COUNT(*) FROM silver_sales WHERE total_sum <= 0;"
    )
    if records_negative[0] > 0:
        raise AirflowException(f"Якість даних порушено! Знайдено {records_negative[0]} чеків з від'ємною або нульовою сумою.")

    # Перевірка 2: Чи є дублікати order_id
    records_duplicates = hook.get_first(
        """
        SELECT COUNT(*) FROM (
            SELECT order_id, COUNT(*) 
            FROM silver_sales 
            GROUP BY order_id 
            HAVING COUNT(*) > 1
        ) t;
        """
    )
    if records_duplicates[0] > 0:
        raise AirflowException(f"Якість даних порушено! Знайдено {records_duplicates[0]} дублікатів order_id.")

    print("Усі перевірки якості даних успішно пройдено!")

with DAG(
    'iiko_restaurant_etl_pipeline',
    default_args=default_args,
    description='Пайплайн ресторанної аналітики iiko: Bronze -> Silver -> Gold',
    schedule_interval='@hourly',  # Запуск щогодини (або можна змінити)
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=['iiko', 'etl', 'restaurant'],
) as dag:

    # Завдання 1: Генерація та завантаження мокових даних у Bronze (R2)
    t1_generate_bronze = PythonOperator(
        task_id='generate_and_upload_bronze',
        python_callable=generate_and_upload_sales,
    )

    # Завдання 2: Інкрементальний ETL у Silver (PostgreSQL)
    t2_transform_silver = PythonOperator(
         task_id='run_silver_etl',
         python_callable=run_incremental_etl,
    )

    # Завдання 3: Оновлення вітрин Gold шару
    t3_create_gold = PythonOperator(
         task_id='refresh_gold_views',
         python_callable=create_gold_views,
     )

    # Завдання 4: Перевірка якості даних
    t4_check_quality = PythonOperator(
        task_id='check_data_quality',
        python_callable=check_data_quality,
    )

    t1_generate_bronze >> t2_transform_silver >> t3_create_gold >> t4_check_quality
