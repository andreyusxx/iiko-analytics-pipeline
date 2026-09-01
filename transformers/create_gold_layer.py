import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def build_gold_layer():
    print("Крок 1: Підключення до бази даних Neon для побудови Gold-шару...")
    conn = get_db_connection()
    
    with conn.cursor() as cur:
        print("Створення вітрини: Денні продажі (gold_daily_sales)...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS gold_daily_sales AS
            SELECT 
                DATE(open_time) AS sale_date,
                COUNT(DISTINCT uniq_order_id) AS total_orders,
                COUNT(id) AS total_sold_items,
                SUM(dish_sum) AS gross_revenue,
                SUM(discount_sum) AS total_discounts,
                SUM(dish_sum - discount_sum) AS net_revenue
            FROM silver_guest_checks
            WHERE open_time IS NOT NULL
            GROUP BY DATE(open_time);
        """)

        print("Створення вітрини: ТОП страв (gold_top_dishes)...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS gold_top_dishes AS
            SELECT 
                dish_name,
                COUNT(id) AS times_ordered,
                SUM(dish_sum) AS total_revenue
            FROM silver_guest_checks
            WHERE dish_name IS NOT NULL
              AND dish_name NOT IN ('Гарний настрій')
            GROUP BY dish_name
            ORDER BY times_ordered DESC;
        """)

        print("Створення вітрини: Ефективність касирів (gold_cashier_performance)...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS gold_cashier_performance AS
            SELECT 
                cashier,
                COUNT(DISTINCT uniq_order_id) AS orders_handled,
                SUM(dish_sum) AS revenue_generated
            FROM silver_guest_checks
            WHERE cashier IS NOT NULL
            GROUP BY cashier
            ORDER BY revenue_generated DESC;
        """)

    conn.commit()
    conn.close()
    print("🚀 Gold-шар успішно побудовано! Вітрини готові до підключення в Metabase.")

if __name__ == "__main__":
    build_gold_layer()