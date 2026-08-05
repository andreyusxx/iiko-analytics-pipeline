import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

def create_gold_views():
    """Створює аналітичні вітрини (Gold шар) у базі даних PostgreSQL."""
    connection = None
    cursor = None
    
    try:
        connection = psycopg2.connect(DATABASE_URL)
        cursor = connection.cursor()
        
        # 1. Вітрина популярності страв (топ за виручкою та кількістю)
        cursor.execute("""
            CREATE OR REPLACE VIEW gold_dish_performance AS
            SELECT 
                dish_id,
                name,
                SUM(quantity) AS total_sold_quantity,
                SUM(price * quantity) AS total_revenue,
                COUNT(DISTINCT order_id) AS orders_count
            FROM silver_sale_items
            GROUP BY dish_id, name
            ORDER BY total_revenue DESC;
        """)
        
        # 2. Вітрина порівняння продажів (звичайні замовлення проти банкетів)
        cursor.execute("""
            CREATE OR REPLACE VIEW gold_sales_summary_by_type AS
            SELECT 
                DATE(datetime) AS sale_date,
                is_banquet,
                COUNT(order_id) AS total_orders,
                SUM(total_sum) AS daily_revenue,
                ROUND(AVG(total_sum), 2) AS average_check
            FROM silver_sales
            GROUP BY DATE(datetime), is_banquet
            ORDER BY sale_date DESC;
        """)
        
        connection.commit()
        print("Аналітичні вітрини шару Gold успішно створено в PostgreSQL!")
        
    except Exception as e:
        if connection:
            connection.rollback()
        print(f"Помилка при створенні Gold шару: {e}")
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

if __name__ == "__main__":
    create_gold_views()