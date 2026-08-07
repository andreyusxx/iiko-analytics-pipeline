import sys
import os
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

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

    t1_generate_bronze >> t2_transform_silver >> t3_create_gold
