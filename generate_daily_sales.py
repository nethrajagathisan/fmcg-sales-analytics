"""
FMCG Daily Sales Simulator
==========================

Generates one day of synthetic-but-realistic FMCG distributor sales as a CSV.

Unlike a naive simulator that draws every field independently (which produces
pure noise and makes downstream "insights" meaningless), this generator builds
deliberate, defensible relationships into the data so that analysis finds REAL
signal:

  * Discount -> volume  : higher discounts lift unit volume, but the lift
                          under-compensates for the price cut, so net revenue
                          per order falls slightly (value-dilutive discounting).
  * Salesperson skill   : some reps genuinely close more orders AND bigger
                          orders, so a performance ranking is meaningful.
  * Region strength     : metro-heavy regions (West, South) are stronger markets
                          on both order count and order size.
  * Category demand     : fast movers (Dairy, Beverages) appear more often.
  * Channel effect      : Distributor orders are bulk; Online orders are small.
  * Day-of-week pattern : weekday restocking peaks (Fri), weekend dips (Sun),
                          producing a real weekly revenue trend.
  * Payment by channel  : bulk Distributor orders skew to Credit; Online to Card/UPI.

Reproducible: the same date always produces the same data (seeded by date).

Usage:
    python generate_daily_sales.py              # generates today's file
    python generate_daily_sales.py 2026-06-22   # backfill a specific date
"""

import pandas as pd
import numpy as np
import random
import os
import sys
from datetime import datetime, date

# ─── CONFIG ───────────────────────────────────────────────────────────────────
OUTPUT_FOLDER = "daily_sales_data"   # folder where CSVs will be dropped
BASE_ORDERS   = 520                  # baseline orders/day before seasonality
DISCOUNT_ELASTICITY = 0.8            # volume lift per 1.0 of discount fraction
                                     # (0.8 => 15% discount lifts units ~+12%,
                                     #  below the ~+17.6% break-even, so deeper
                                     #  discounts gently erode per-order revenue)

# Date to simulate: optional command-line arg (YYYY-MM-DD), else today.
if len(sys.argv) > 1:
    SIMULATE_DATE = datetime.strptime(sys.argv[1], "%Y-%m-%d").date()
else:
    SIMULATE_DATE = date.today()
# ──────────────────────────────────────────────────────────────────────────────

# Seed everything by the date so the same date always reproduces the same file.
DATE_SEED = int(SIMULATE_DATE.strftime("%Y%m%d"))
random.seed(DATE_SEED)
np.random.seed(DATE_SEED)

# ─── REFERENCE DATA ───────────────────────────────────────────────────────────

REGIONS = {
    "North":   ["Delhi", "Chandigarh", "Lucknow", "Jaipur"],
    "South":   ["Bangalore", "Chennai", "Hyderabad", "Kochi"],
    "East":    ["Kolkata", "Bhubaneswar", "Patna", "Guwahati"],
    "West":    ["Mumbai", "Pune", "Ahmedabad", "Surat"],
    "Central": ["Nagpur", "Bhopal", "Indore", "Raipur"],
}

# Region market characteristics:
#   weight   -> how often an order comes from the region (order-count share)
#   strength -> multiplier on order size (affluence / market maturity)
# West & South are the strongest markets; East & Central trail.
REGION_WEIGHT   = {"North": 1.00, "South": 1.20, "East": 0.85, "West": 1.25, "Central": 0.75}
REGION_STRENGTH = {"North": 1.00, "South": 1.08, "East": 0.92, "West": 1.12, "Central": 0.88}

SALESPERSONS = [
    "Arjun Mehta", "Priya Sharma", "Rohan Das", "Sneha Iyer",
    "Vikram Singh", "Divya Nair", "Karan Patel", "Anjali Rao",
    "Nikhil Joshi", "Pooja Verma"
]

# Skill multiplier per rep: drives BOTH how many orders they win (selection
# weight) and how large those orders are (size multiplier). Top performers
# therefore genuinely separate from the pack — a ranking is meaningful.
SALESPERSON_SKILL = {
    "Arjun Mehta": 1.25, "Priya Sharma": 1.20, "Rohan Das": 0.85,
    "Sneha Iyer": 1.10, "Vikram Singh": 0.90, "Divya Nair": 1.15,
    "Karan Patel": 0.80, "Anjali Rao": 1.05, "Nikhil Joshi": 0.95,
    "Pooja Verma": 1.00,
}

# SKU data: category -> list of (product_name, sku_id, unit_price)
SKUS = {
    "Beverages": [
        ("Tropicana Orange 1L",  "BEV-001", 95),
        ("Maaza Mango 600ml",    "BEV-002", 40),
        ("Red Bull 250ml",       "BEV-003", 125),
        ("Bisleri Water 1L",     "BEV-004", 20),
        ("Nescafe Classic 50g",  "BEV-005", 210),
        ("Glucon-D 500g",        "BEV-006", 165),
    ],
    "Snacks": [
        ("Lays Classic 90g",         "SNK-001", 30),
        ("Kurkure Masala 90g",       "SNK-002", 30),
        ("Hide & Seek Cookies 150g", "SNK-003", 55),
        ("Good Day Biscuits 200g",   "SNK-004", 45),
        ("Haldirams Bhujia 400g",    "SNK-005", 130),
        ("Maggi Noodles 70g",        "SNK-006", 14),
    ],
    "Personal Care": [
        ("Dove Soap 100g",          "PC-001", 55),
        ("Head & Shoulders 340ml",  "PC-002", 290),
        ("Colgate Toothpaste 200g", "PC-003", 110),
        ("Nivea Lotion 200ml",      "PC-004", 220),
        ("Dettol Hand Wash 250ml",  "PC-005", 95),
        ("Gillette Mach3 Razor",    "PC-006", 350),
    ],
    "Household": [
        ("Ariel Detergent 1kg",    "HH-001", 220),
        ("Vim Dishwash Gel 500ml", "HH-002", 90),
        ("Lizol Floor Cleaner 1L", "HH-003", 175),
        ("Harpic Toilet Cleaner",  "HH-004", 140),
        ("Good Knight Refill",     "HH-005", 75),
        ("Scotch Brite Scrub Pad", "HH-006", 45),
    ],
    "Dairy": [
        ("Amul Full Cream Milk 1L",  "DAI-001", 68),
        ("Amul Butter 500g",         "DAI-002", 260),
        ("Mother Dairy Curd 400g",   "DAI-003", 50),
        ("Nestle Munch Milkshake",   "DAI-004", 30),
        ("Britannia Cheese Slice",   "DAI-005", 115),
        ("Amul Ice Cream 750ml",     "DAI-006", 195),
    ],
}

# Category demand weights — fast-moving categories appear more often.
CATEGORY_WEIGHT = {"Beverages": 1.20, "Snacks": 1.10, "Personal Care": 0.90,
                   "Household": 0.80, "Dairy": 1.30}

# Base quantity range (units per order) by category.
QTY_RANGE = {"Beverages": (5, 40), "Snacks": (10, 60), "Personal Care": (3, 20),
             "Household": (3, 25), "Dairy": (5, 35)}

# Channel: selection weight (how common) and size factor (bulk vs small basket).
CHANNELS       = ["In-Store", "Distributor", "Online"]
CHANNEL_WEIGHT = {"In-Store": 1.00, "Distributor": 0.80, "Online": 0.60}
CHANNEL_FACTOR = {"In-Store": 1.00, "Distributor": 1.40, "Online": 0.70}

# Payment mix depends on channel: bulk Distributor orders lean on trade Credit,
# Online leans on Card/UPI. Order matches PAYMENT_METHODS below.
PAYMENT_METHODS = ["Cash", "Card", "UPI", "Credit"]
PAYMENT_WEIGHT  = {
    "In-Store":    [0.35, 0.20, 0.40, 0.05],
    "Distributor": [0.10, 0.15, 0.25, 0.50],
    "Online":      [0.05, 0.45, 0.45, 0.05],
}

# Discount tiers, weighted towards no discount.
DISCOUNTS = [0, 0, 0, 0, 5, 5, 10, 15]

# Day-of-week order-volume multiplier (Mon=0 ... Sun=6): weekday restocking
# peaks toward Friday; weekends — especially Sunday — are quiet.
DOW_VOLUME = {0: 1.10, 1: 1.05, 2: 1.00, 3: 1.05, 4: 1.15, 5: 0.90, 6: 0.55}

# ─── CUSTOMER POOL (fixed pool so repeat customers appear) ────────────────────
FIRST_NAMES = ["Amit","Priya","Rahul","Sunita","Vikram","Deepa","Raj","Meena",
                "Suresh","Kavya","Arun","Neha","Sanjay","Pooja","Ravi","Anita",
                "Manoj","Geeta","Ajay","Rekha","Sunil","Shweta","Ramesh","Usha"]
LAST_NAMES  = ["Sharma","Verma","Singh","Patel","Kumar","Rao","Nair","Joshi",
                "Mehta","Iyer","Das","Gupta","Mishra","Pillai","Reddy","Shah"]

random.seed(42)  # fixed seed for customer pool (stable across all dates)
CUSTOMER_POOL = [
    (f"CUST{str(i).zfill(4)}", f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}")
    for i in range(1, 301)
]
random.seed(DATE_SEED)  # restore daily seed

# ─── DERIVED SELECTION VECTORS ────────────────────────────────────────────────
region_names  = list(REGION_WEIGHT.keys())
region_w      = list(REGION_WEIGHT.values())
category_names = list(CATEGORY_WEIGHT.keys())
category_w    = list(CATEGORY_WEIGHT.values())
salesperson_w = [SALESPERSON_SKILL[s] for s in SALESPERSONS]
channel_w     = [CHANNEL_WEIGHT[c] for c in CHANNELS]

# Number of orders for the day follows the weekly pattern (reproducible).
dow  = SIMULATE_DATE.weekday()
ROWS = int(round(BASE_ORDERS * DOW_VOLUME[dow] * random.uniform(0.92, 1.08)))

# ─── GENERATE ROWS ────────────────────────────────────────────────────────────

records = []
for i in range(1, ROWS + 1):
    region      = random.choices(region_names, weights=region_w)[0]
    city        = random.choice(REGIONS[region])
    category    = random.choices(category_names, weights=category_w)[0]
    product     = random.choice(SKUS[category])
    cust        = random.choice(CUSTOMER_POOL)
    salesperson = random.choices(SALESPERSONS, weights=salesperson_w)[0]
    channel     = random.choices(CHANNELS, weights=channel_w)[0]
    discount    = random.choice(DISCOUNTS)
    hour        = random.randint(9, 20)
    minute      = random.randint(0, 59)
    second      = random.randint(0, 59)

    # Order size = base demand, scaled by the real drivers, plus random noise.
    base_qty   = random.randint(*QTY_RANGE[category])
    size_factor = (REGION_STRENGTH[region]
                   * SALESPERSON_SKILL[salesperson]
                   * CHANNEL_FACTOR[channel]
                   * (1 + DISCOUNT_ELASTICITY * discount / 100.0))
    qty = max(1, int(round(base_qty * size_factor * random.uniform(0.85, 1.15))))

    payment     = random.choices(PAYMENT_METHODS, weights=PAYMENT_WEIGHT[channel])[0]
    return_flag = "Yes" if random.random() < 0.05 else "No"

    records.append({
        "order_id":        f"ORD-{SIMULATE_DATE.strftime('%Y%m%d')}-{str(i).zfill(4)}",
        "order_date":      SIMULATE_DATE.strftime("%Y-%m-%d"),
        "order_time":      f"{str(hour).zfill(2)}:{str(minute).zfill(2)}:{str(second).zfill(2)}",
        "customer_id":     cust[0],
        "customer_name":   cust[1],
        "region":          region,
        "city":            city,
        "salesperson":     salesperson,
        "category":        category,
        "product_name":    product[0],
        "sku_id":          product[1],
        "quantity":        qty,
        "unit_price":      product[2],
        "discount_pct":    discount,
        "return_flag":     return_flag,
        "payment_method":  payment,
        "channel":         channel,
    })

df = pd.DataFrame(records)

# ─── INJECT INTENTIONAL DIRT (so the cleaning layer has real work to do) ──────
# ~2% blank customer names
blank_idx = df.sample(frac=0.02).index
df.loc[blank_idx, "customer_name"] = ""

# ~1% duplicate order IDs (copy some rows)
dup_idx = df.sample(frac=0.01).index
df = pd.concat([df, df.loc[dup_idx]], ignore_index=True)

# ~1% negative quantity (data entry error)
neg_idx = df.sample(frac=0.01).index
df.loc[neg_idx, "quantity"] = df.loc[neg_idx, "quantity"] * -1

# ~1% missing region
missing_idx = df.sample(frac=0.01).index
df.loc[missing_idx, "region"] = ""

# shuffle so dirt isn't all at the end
df = df.sample(frac=1).reset_index(drop=True)

# ─── SAVE ─────────────────────────────────────────────────────────────────────
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
filename = os.path.join(OUTPUT_FOLDER, f"sales_{SIMULATE_DATE.strftime('%Y_%m_%d')}.csv")
df.to_csv(filename, index=False)

print(f"Generated: {filename}  |  Rows: {len(df)}  |  Date: {SIMULATE_DATE} ({SIMULATE_DATE.strftime('%A')})")
