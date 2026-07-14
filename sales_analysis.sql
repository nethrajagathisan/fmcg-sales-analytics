-- FMCG Sales Analysis SQL Queries
-- Run with: sqlite3 fmcg_sales.db < sales_analysis.sql
-- These queries answer real business questions a manager would ask

-- ==============================================================================
-- QUERY 1: SALESPERSON PERFORMANCE RANKING
-- Business Question: Who is our top performer? Where should we allocate bonuses?
-- ==============================================================================
.mode column
.header on
.print
.print "QUERY 1: SALESPERSON REVENUE RANKING"
.print "Top salespersons by total revenue (excluding returns, no duplicates)"
.print
SELECT
    RANK() OVER (ORDER BY SUM(revenue) DESC) as revenue_rank,
    salesperson,
    COUNT(DISTINCT order_id) as total_orders,
    ROUND(SUM(revenue), 2) as total_revenue,
    ROUND(100.0 * SUM(revenue) / SUM(SUM(revenue)) OVER (), 1) as pct_of_total,
    ROUND(AVG(revenue), 2) as avg_order_value
FROM sales_clean
GROUP BY salesperson
ORDER BY total_revenue DESC;


-- ==============================================================================
-- QUERY 2: CATEGORY PERFORMANCE & PROFITABILITY
-- Business Question: Which product categories are our profit drivers?
-- ==============================================================================
.print
.print "QUERY 2: REVENUE BY PRODUCT CATEGORY"
.print "Shows which categories drive revenue and average margins"
.print
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
ORDER BY total_revenue DESC;


-- ==============================================================================
-- QUERY 3: REGIONAL PERFORMANCE ANALYSIS
-- Business Question: Which regions are lagging? Where should we invest?
-- ==============================================================================
.print
.print "QUERY 3: REVENUE BY REGION"
.print "Identifies strong vs weak regions for strategy planning"
.print
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
ORDER BY total_revenue DESC;


-- ==============================================================================
-- QUERY 4: DAILY REVENUE TREND
-- Business Question: Is our revenue growing or declining? Spot weekly patterns
-- ==============================================================================
.print
.print "QUERY 4: DAILY REVENUE TREND (Week of June 22-29)"
.print "Shows daily performance and helps predict seasonality"
.print
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
ORDER BY order_date;


-- ==============================================================================
-- QUERY 5: TOP 10 PRODUCTS BY REVENUE
-- Business Question: What are our bestsellers? Stock them well.
-- ==============================================================================
.print
.print "QUERY 5: TOP 10 PRODUCTS BY REVENUE"
.print "Identify the revenue cash cows worth protecting"
.print
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
LIMIT 10;


-- ==============================================================================
-- QUERY 6: IMPACT OF DISCOUNTS ON REVENUE
-- Business Question: Are heavy discounts hurting profitability?
-- ==============================================================================
.print
.print "QUERY 6: DISCOUNT IMPACT ANALYSIS"
.print "Does discounting actually increase revenue or just margin erosion?"
.print
SELECT
    discount_pct,
    COUNT(DISTINCT order_id) as order_count,
    ROUND(SUM(quantity), 0) as units_sold,
    ROUND(SUM(revenue), 2) as total_revenue,
    ROUND(AVG(revenue), 2) as avg_order_value,
    ROUND(SUM(quantity * unit_price) - SUM(revenue), 2) as total_discount_given
FROM sales_clean
GROUP BY discount_pct
ORDER BY discount_pct;


-- ==============================================================================
-- QUERY 7: PAYMENT METHOD DISTRIBUTION
-- Business Question: How are customers paying? Cash handling costs?
-- ==============================================================================
.print
.print "QUERY 7: PAYMENT METHOD BREAKDOWN"
.print "Understand cash flow and payment preferences"
.print
SELECT
    payment_method,
    COUNT(DISTINCT order_id) as order_count,
    ROUND(100.0 * COUNT(DISTINCT order_id) / (SELECT COUNT(DISTINCT order_id) FROM sales_clean), 1) as pct_of_orders,
    ROUND(SUM(revenue), 2) as total_revenue,
    ROUND(100.0 * SUM(revenue) / (SELECT SUM(revenue) FROM sales_clean), 1) as pct_of_revenue,
    ROUND(AVG(revenue), 2) as avg_order_value
FROM sales_clean
GROUP BY payment_method
ORDER BY total_revenue DESC;


-- ==============================================================================
-- QUERY 8: SALES CHANNEL PERFORMANCE
-- Business Question: Is online/distributor worth the effort or is in-store key?
-- ==============================================================================
.print
.print "QUERY 8: SALES CHANNEL COMPARISON"
.print "Evaluate ROI of each distribution channel"
.print
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
ORDER BY channel_revenue DESC;


-- ==============================================================================
-- QUERY 9: SALESPERSON TARGET vs ACTUAL  (JOIN + WINDOW FUNCTION)
-- Business Question: Who is hitting their weekly quota? Who needs coaching?
-- ==============================================================================
.print
.print "QUERY 9: TARGET vs ACTUAL ATTAINMENT"
.print "Joins actual revenue to each rep's weekly target and ranks by attainment"
.print
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
ORDER BY attainment_pct DESC;
