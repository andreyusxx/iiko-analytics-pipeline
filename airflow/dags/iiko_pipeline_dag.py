import sys
import os
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.exceptions import AirflowException

# Додаємо шлях до нашого проєкту в системний шлях Python всередині контейнера
sys.path.insert(0, '/opt/airflow/project')

# Імпортуємо актуальні функції для пайплайну
from extractors.syrve_сhecks_scraper import intercept_checks_by_date  
from loaders.syrve_silver_loader import process_new_files  
from transformers.create_gold_layer import build_gold_layer 

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
    
    # Перевірка 1: Чи є від'ємні або нульові чеки в silver_guest_checks
    records_negative = hook.get_first(
        "SELECT COUNT(*) FROM public.silver_guest_checks WHERE dish_sum < 0;"
    )
    if records_negative[0] > 0:
        raise AirflowException(f"Якість даних порушено! Знайдено {records_negative[0]} позицій з від'ємною сумою.")

    print("Усі перевірки якості даних успішно пройдено!")

with DAG(
    'iiko_restaurant_etl_pipeline',
    default_args=default_args,
    description='Пайплайн ресторанної аналітики Syrve: Bronze -> Silver -> Gold',
    schedule_interval='@hourly',  # Запуск щогодини
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=['syrve', 'etl', 'restaurant'],
) as dag:

    # Завдання 1: Запит до Syrve API та збереження сирих даних у Bronze (Cloudflare R2)
    t1_extract_bronze = PythonOperator(
        task_id='extract_syrve_to_bronze',
        python_callable=intercept_checks_by_date,
    )

    # Завдання 2: Очищення та збагачення даних у Silver (PostgreSQL / Neon) з категоріями
    t2_transform_silver = PythonOperator(
         task_id='run_silver_etl',
         python_callable=process_new_files,
    )

    # Завдання 3: Оновлення вітрин Gold шару (включно з категоріями)
    t3_create_gold = PythonOperator(
         task_id='refresh_gold_views',
         python_callable=build_gold_layer,
    )

    # Завдання 4: Перевірка якості даних
    t4_check_quality = PythonOperator(
        task_id='check_data_quality',
        python_callable=check_data_quality,
    )

    # Послідовність виконання задач у DAG
    t1_extract_bronze >> t2_transform_silver >> t3_create_gold >> t4_check_quality