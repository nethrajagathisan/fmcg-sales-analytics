"""
Load all sales CSVs into SQLite database for analysis.
Run once: python load_to_database.py
"""

import pandas as pd
import sqlite3
import glob
from pathlib import Path

# Create/connect to SQLite database
db_path = "fmcg_sales.db"
conn = sqlite3.connect(db_path)

# Read all CSVs and combine
csv_files = sorted(glob.glob("daily_sales_data/*.csv"))
dfs = [pd.read_csv(f) for f in csv_files]
df = pd.concat(dfs, ignore_index=True)

print(f"Loaded {len(df)} rows from {len(csv_files)} CSV files")

# Load into SQLite (overwrites if exists)
df.to_sql("sales", conn, if_exists="replace", index=False)

# Create a clean view (handles dirty data)
conn.execute("DROP VIEW IF EXISTS sales_clean")
conn.execute("""
CREATE VIEW sales_clean AS
SELECT
    order_id,
    order_date,
    order_time,
    customer_id,
    COALESCE(NULLIF(customer_name, ''), 'Unknown Customer') as customer_name,
    COALESCE(NULLIF(region, ''), 'Unknown Region') as region,
    city,
    salesperson,
    category,
    product_name,
    sku_id,
    ABS(quantity) as quantity,
    unit_price,
    discount_pct,
    return_flag,
    payment_method,
    channel,
    unit_price * ABS(quantity) * (1 - discount_pct/100.0) as revenue
FROM (
    -- Keep the FIRST copy of each order_id (matches the pandas keep='first'
    -- dedup used in analyze_sales.py, so SQL/EDA/stats stay consistent).
    SELECT *, ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY rowid) AS _rn
    FROM sales
    WHERE return_flag = 'No'
)
WHERE _rn = 1
""")

# Salesperson weekly revenue targets — a small dimension table so analysis can
# JOIN actuals to quotas and compute target-vs-actual attainment.
conn.execute("DROP TABLE IF EXISTS targets")
conn.execute("""
CREATE TABLE targets (
    salesperson   TEXT PRIMARY KEY,
    weekly_target REAL
)
""")
WEEKLY_TARGET = 900000  # uniform weekly revenue quota per rep (INR)
salespeople = [row[0] for row in conn.execute(
    "SELECT DISTINCT salesperson FROM sales").fetchall()]
conn.executemany(
    "INSERT INTO targets VALUES (?, ?)",
    [(sp, WEEKLY_TARGET) for sp in salespeople]
)

conn.commit()
conn.close()

print(f"[SUCCESS] Database created: {db_path}")
print("[SUCCESS] View created: sales_clean (cleaned data, no returns, no duplicates)")
print(f"[SUCCESS] Targets table created: {len(salespeople)} reps @ Rs. {WEEKLY_TARGET:,}/week")
print("\nNext: Run SQL queries with: sqlite3 fmcg_sales.db < sales_analysis.sql")
