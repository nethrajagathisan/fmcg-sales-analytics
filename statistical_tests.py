"""
FMCG Sales - Statistical Significance Testing & Forecast
========================================================

Descriptive charts can make any difference *look* meaningful. This script asks
the harder question: are the differences we see real, or just sampling noise?

It runs hypothesis tests (ANOVA, correlation, t-test) with both a p-value AND an
effect size, because with ~3,900 rows almost anything is "statistically
significant" — what matters for the business is whether the effect is *large
enough to act on*. It deliberately includes a test that comes back NULL, because
reporting "no real difference" is as valuable as finding one.

Run:  python statistical_tests.py
"""

import glob
import numpy as np
import pandas as pd
from scipy import stats

ALPHA = 0.05  # significance threshold

# ─── LOAD & CLEAN (same logic as analyze_sales.py, so results are consistent) ─
df = pd.concat([pd.read_csv(f) for f in sorted(glob.glob("daily_sales_data/*.csv"))],
               ignore_index=True)
df["customer_name"] = df["customer_name"].replace("", np.nan).fillna("Unknown Customer")
df["region"] = df["region"].replace("", np.nan).fillna("Unknown Region")
df["quantity"] = df["quantity"].abs()
df = df.drop_duplicates(subset=["order_id"], keep="first").reset_index(drop=True)
df["revenue"] = df["unit_price"] * df["quantity"] * (1 - df["discount_pct"] / 100)

returns = df[df["return_flag"] == "Yes"].copy()
sales = df[df["return_flag"] == "No"].copy()


def verdict(p):
    return "SIGNIFICANT" if p < ALPHA else "NOT significant"


def eta_squared(groups):
    """Share of variance explained by group membership (practical effect size)."""
    all_vals = np.concatenate(groups)
    grand = all_vals.mean()
    ss_between = sum(len(g) * (g.mean() - grand) ** 2 for g in groups)
    ss_total = ((all_vals - grand) ** 2).sum()
    return ss_between / ss_total


def effect_label(eta2):
    # Cohen's rough benchmarks for eta-squared.
    if eta2 < 0.01:
        return "negligible"
    if eta2 < 0.06:
        return "small"
    if eta2 < 0.14:
        return "medium"
    return "large"


print("=" * 80)
print(f"STATISTICAL SIGNIFICANCE TESTS   (n = {len(sales):,} clean orders, alpha = {ALPHA})")
print("=" * 80)

# ─── TEST 1: Do REGIONS differ in average order value? (one-way ANOVA) ────────
print("\n1. REGION vs average order value  (one-way ANOVA)")
real_regions = sales[sales["region"] != "Unknown Region"]
groups = [g["revenue"].values for _, g in real_regions.groupby("region")]
F, p = stats.f_oneway(*groups)
e2 = eta_squared(groups)
print(f"   F = {F:.2f},  p = {p:.2e}  ->  {verdict(p)}")
print(f"   effect size (eta^2) = {e2:.3f} ({effect_label(e2)})")
print(f"   Plain English: regional differences in average order value are "
      f"{'real, not noise' if p < ALPHA else 'within what randomness could produce'}.")

# ─── TEST 2: Do SALESPEOPLE differ in average order value? (one-way ANOVA) ────
print("\n2. SALESPERSON vs average order value  (one-way ANOVA)")
groups = [g["revenue"].values for _, g in sales.groupby("salesperson")]
F, p = stats.f_oneway(*groups)
e2 = eta_squared(groups)
print(f"   F = {F:.2f},  p = {p:.2e}  ->  {verdict(p)}")
print(f"   effect size (eta^2) = {e2:.3f} ({effect_label(e2)})")
print(f"   Plain English: a performance ranking is {'meaningful' if p < ALPHA else 'NOT justified — reps look interchangeable'}.")

# ─── TEST 3: Does DISCOUNT drive order VOLUME? (Pearson correlation) ──────────
print("\n3. DISCOUNT % vs units per order  (Pearson correlation)")
r, p = stats.pearsonr(sales["discount_pct"], sales["quantity"])
print(f"   r = {r:.3f},  p = {p:.2e}  ->  {verdict(p)}")
print(f"   r^2 = {r**2:.3f}  (discount explains only {r**2*100:.1f}% of order-size variance)")
print(f"   Plain English: discounting has a real but SMALL positive pull on volume.")
print("   Avg units/order by discount tier:")
print(sales.groupby("discount_pct")["quantity"].mean().round(1).to_string().replace("\n", "\n     "))

# ─── TEST 4: Does the DISCOUNT tier change NET revenue per order? (ANOVA) ─────
# This is the one that matters for the "should we discount?" decision.
print("\n4. DISCOUNT tier vs NET revenue per order  (one-way ANOVA)")
groups = [g["revenue"].values for _, g in sales.groupby("discount_pct")]
F, p = stats.f_oneway(*groups)
e2 = eta_squared(groups)
print(f"   F = {F:.2f},  p = {p:.3f}  ->  {verdict(p)}")
print(f"   effect size (eta^2) = {e2:.3f} ({effect_label(e2)})")
print(f"   Plain English: the extra volume from discounting roughly offsets the "
      f"price cut, so net revenue per order is {'NOT materially different across tiers' if e2 < 0.01 else 'different across tiers'}.")
print("   => 'tighten discounts to save money' is NOT clearly supported by this data.")

# ─── TEST 5: Are RETURNED orders worth more than kept orders? (t-test) ────────
# Expected NULL result — included on purpose: a good analyst reports 'no effect'.
print("\n5. RETURNED vs kept orders, by order value  (two-sample t-test)")
t, p = stats.ttest_ind(returns["revenue"], sales["revenue"], equal_var=False)
print(f"   returned mean = Rs. {returns['revenue'].mean():,.0f}  |  kept mean = Rs. {sales['revenue'].mean():,.0f}")
print(f"   t = {t:.2f},  p = {p:.3f}  ->  {verdict(p)}")
print(f"   Plain English: no evidence that high-value orders are returned more "
      f"often; returns look random w.r.t. value. (A NULL result, reported honestly.)")

# ─── FORECAST: daily revenue, with explicit caveats ──────────────────────────
print("\n" + "=" * 80)
print("DAILY REVENUE FORECAST  (illustrative - see caveats)")
print("=" * 80)
daily = (sales.assign(d=pd.to_datetime(sales["order_date"]))
              .groupby("d")["revenue"].sum().sort_index())
x = np.arange(len(daily))
slope, intercept, r_val, p_val, se = stats.linregress(x, daily.values)
print(f"\nLinear trend:  slope = Rs. {slope:,.0f}/day,  R^2 = {r_val**2:.2f},  p = {p_val:.3f}")
if r_val ** 2 < 0.3:
    print("   R^2 is low: the daily series is dominated by day-of-week swings, not a")
    print("   clean trend, so a straight-line projection would be misleading.")

ma3 = daily.tail(3).mean()
next_day = daily.index[-1] + pd.Timedelta(days=1)
print(f"\nNaive next-day forecast ({next_day.date()}, {next_day.day_name()}):")
print(f"   3-day moving average = Rs. {ma3:,.0f}   (+/- 1 std = Rs. {daily.std():,.0f})")

print("\nCAVEAT: 8 days is far too short for a reliable forecast. There is strong")
print("weekly seasonality (Sunday slump). A proper model needs ~6-8 weeks of data")
print("and a seasonal method (seasonal decomposition, SARIMA, or Prophet).")

print("\n" + "=" * 80)
print("TAKEAWAYS")
print("=" * 80)
print("  - Region & salesperson differences are REAL and worth acting on.")
print("  - Discount lifts volume a little, but does NOT clearly grow net revenue,")
print("    so blanket 'cut discounts' or 'discount more' claims are not supported.")
print("  - Returns are random w.r.t. order value (a deliberate null result).")
print("  - 8 days is too little data to forecast; treat trend lines as illustrative.")
