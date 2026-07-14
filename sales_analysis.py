"""
Run SQL analysis queries and display results nicely
"""
import sqlite3
import pandas as pd

conn = sqlite3.connect("fmcg_sales.db")

queries = {
    "1. SALESPERSON PERFORMANCE RANKING": """
        SELECT
            RANK() OVER (ORDER BY SUM(revenue) DESC) as revenue_rank,
            salesperson,
            COUNT(DISTINCT order_id) as total_orders,
            ROUND(SUM(revenue), 2) as total_revenue,
            ROUND(100.0 * SUM(revenue) / SUM(SUM(revenue)) OVER (), 1) as pct_of_total,
            ROUND(AVG(revenue), 2) as avg_order_value
        FROM sales_clean
        GROUP BY salesperson
        ORDER BY total_revenue DESC
    """,

    "2. REVENUE BY PRODUCT CATEGORY": """
        SELECT
            category,
            COUNT(DISTINCT order_id) as order_count,
            COUNT(DISTINCT product_name) as product_variety,
            ROUND(SUM(quantity), 0) as units_sold,
            ROUND(SUM(revenue), 2) as total_revenue,
            ROUND(AVG(revenue), 2) as avg_order_value,
            ROUND(100.0 * SUM(discount_pct * quantity) / SUM(quantity), 2) as avg_discount_given
        FROM sales_clean
        GROUP BY category
        ORDER BY total_revenue DESC
    """,

    "3. REVENUE BY REGION": """
        SELECT
            region,
            COUNT(DISTINCT salesperson) as salespeople_count,
            COUNT(DISTINCT customer_id) as unique_customers,
            COUNT(DISTINCT order_id) as order_count,
            ROUND(SUM(quantity), 0) as total_units,
            ROUND(SUM(revenue), 2) as total_revenue,
            ROUND(AVG(revenue), 2) as avg_order_value,
            ROUND(SUM(revenue) / COUNT(DISTINCT salesperson), 2) as revenue_per_salesperson
        FROM sales_clean
        GROUP BY region
        ORDER BY total_revenue DESC
    """,

    "4. DAILY REVENUE TREND": """
        SELECT
            order_date,
            COUNT(DISTINCT order_id) as orders,
            ROUND(SUM(revenue), 2) as daily_revenue,
            ROUND(SUM(SUM(revenue)) OVER (ORDER BY order_date), 2) as cumulative_revenue,
            ROUND(SUM(revenue) - LAG(SUM(revenue)) OVER (ORDER BY order_date), 2) as day_over_day_change,
            ROUND(100.0 * (SUM(revenue) - LAG(SUM(revenue)) OVER (ORDER BY order_date))
                  / LAG(SUM(revenue)) OVER (ORDER BY order_date), 1) as day_over_day_pct
        FROM sales_clean
        GROUP BY order_date
        ORDER BY order_date
    """,

    "5. TOP 10 PRODUCTS BY REVENUE": """
        SELECT
            product_name,
            sku_id,
            category,
            ROUND(SUM(quantity), 0) as units_sold,
            ROUND(SUM(revenue), 2) as product_revenue,
            ROUND(AVG(revenue), 2) as avg_order_value,
            COUNT(DISTINCT order_id) as order_count,
            ROUND(100.0 * COUNT(DISTINCT order_id) / (SELECT COUNT(DISTINCT order_id) FROM sales_clean), 1) as pct_of_total_orders
        FROM sales_clean
        GROUP BY sku_id, product_name, category
        ORDER BY product_revenue DESC
        LIMIT 10
    """,

    "6. DISCOUNT IMPACT ANALYSIS": """
        SELECT
            discount_pct,
            COUNT(DISTINCT order_id) as order_count,
            ROUND(SUM(quantity), 0) as units_sold,
            ROUND(SUM(revenue), 2) as total_revenue,
            ROUND(AVG(revenue), 2) as avg_order_value,
            ROUND(SUM(quantity * unit_price) - SUM(revenue), 2) as total_discount_given
        FROM sales_clean
        GROUP BY discount_pct
        ORDER BY discount_pct
    """,

    "7. PAYMENT METHOD BREAKDOWN": """
        SELECT
            payment_method,
            COUNT(DISTINCT order_id) as order_count,
            ROUND(100.0 * COUNT(DISTINCT order_id) / (SELECT COUNT(DISTINCT order_id) FROM sales_clean), 1) as pct_of_orders,
            ROUND(SUM(revenue), 2) as total_revenue,
            ROUND(100.0 * SUM(revenue) / (SELECT SUM(revenue) FROM sales_clean), 1) as pct_of_revenue,
            ROUND(AVG(revenue), 2) as avg_order_value
        FROM sales_clean
        GROUP BY payment_method
        ORDER BY total_revenue DESC
    """,

    "8. SALES CHANNEL COMPARISON": """
        SELECT
            channel,
            COUNT(DISTINCT order_id) as order_count,
            COUNT(DISTINCT salesperson) as salespeople_involved,
            COUNT(DISTINCT customer_id) as unique_customers,
            ROUND(SUM(revenue), 2) as channel_revenue,
            ROUND(100.0 * SUM(revenue) / (SELECT SUM(revenue) FROM sales_clean), 1) as pct_of_total_revenue,
            ROUND(AVG(revenue), 2) as avg_order_value,
            ROUND(SUM(revenue) / COUNT(DISTINCT customer_id), 2) as revenue_per_customer
        FROM sales_clean
        GROUP BY channel
        ORDER BY channel_revenue DESC
    """,

    "9. TARGET vs ACTUAL ATTAINMENT (JOIN + WINDOW)": """
        SELECT
            RANK() OVER (ORDER BY SUM(s.revenue) DESC) as rank,
            s.salesperson,
            ROUND(SUM(s.revenue), 2) as actual_revenue,
            t.weekly_target,
            ROUND(100.0 * SUM(s.revenue) / t.weekly_target, 1) as attainment_pct,
            CASE WHEN SUM(s.revenue) >= t.weekly_target THEN 'On Target' ELSE 'Below Target' END as status
        FROM sales_clean s
        JOIN targets t ON s.salesperson = t.salesperson
        GROUP BY s.salesperson, t.weekly_target
        ORDER BY attainment_pct DESC
    """
}

for title, query in queries.items():
    print("\n" + "="*80)
    print(title)
    print("="*80)
    df = pd.read_sql_query(query, conn)
    print(df.to_string(index=False))

conn.close()
