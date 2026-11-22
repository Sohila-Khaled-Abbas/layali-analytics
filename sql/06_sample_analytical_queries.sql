-- ==============================================================================
-- Script 06: Ten Analytical Business Queries for Layali Analytics
-- T-SQL dialect for Microsoft SQL Server
-- ==============================================================================

USE [LayaliAnalytics];
GO

-- ------------------------------------------------------------------------------
-- 1. Monthly Performance Summary (Net Sales, Cost, Margin, Delivery Commission)
-- Grain: Month
-- ------------------------------------------------------------------------------
SELECT
    d.[year_month],
    COUNT(o.[order_id])                                                  AS [completed_orders],
    SUM(o.[net_sales_sar])                                              AS [total_net_sales_sar],
    SUM(o.[food_cost_sar])                                              AS [total_food_cost_sar],
    SUM(o.[delivery_commission_sar])                                    AS [total_delivery_commission_sar],
    SUM(o.[contribution_sar])                                           AS [total_contribution_sar],
    CAST(ROUND((SUM(o.[net_sales_sar]) - SUM(o.[food_cost_sar])) 
        / NULLIF(SUM(o.[net_sales_sar]), 0) * 100.0, 2) AS DECIMAL(5,2)) AS [gross_margin_pct],
    CAST(ROUND(SUM(o.[contribution_sar]) 
        / NULLIF(SUM(o.[net_sales_sar]), 0) * 100.0, 2) AS DECIMAL(5,2)) AS [contribution_margin_pct]
FROM [marts].[fact_orders] o
INNER JOIN [marts].[dim_date] d ON o.[date] = d.[date]
GROUP BY d.[year_month]
ORDER BY d.[year_month];
GO

-- ------------------------------------------------------------------------------
-- 2. Branch Performance & Average Order Value (AOV)
-- Grain: Branch
-- ------------------------------------------------------------------------------
SELECT
    b.[branch_id],
    b.[branch_name],
    COUNT(o.[order_id])                                                    AS [order_count],
    SUM(o.[net_sales_sar])                                                AS [total_net_sales_sar],
    CAST(ROUND(AVG(o.[net_sales_sar]), 2) AS DECIMAL(10,2))              AS [aov_sar],
    CAST(ROUND(AVG(CAST(o.[line_count] AS FLOAT)), 2) AS DECIMAL(5,2))   AS [avg_items_per_order],
    SUM(o.[contribution_sar])                                             AS [total_contribution_sar]
FROM [marts].[fact_orders] o
INNER JOIN [marts].[dim_branch] b ON o.[branch_id] = b.[branch_id]
GROUP BY b.[branch_id], b.[branch_name]
ORDER BY [total_net_sales_sar] DESC;
GO

-- ------------------------------------------------------------------------------
-- 3. The "Obhur Shift" Anomaly Investigation (Monthly Volume & Delivery Mix)
-- Grain: Branch x Month
-- ------------------------------------------------------------------------------
SELECT
    b.[branch_name],
    d.[year_month],
    COUNT(o.[order_id])                                                    AS [total_orders],
    SUM(CASE WHEN o.[channel] = N'delivery' THEN 1 ELSE 0 END)            AS [delivery_orders],
    CAST(ROUND(
        SUM(CASE WHEN o.[channel] = N'delivery' THEN 1.0 ELSE 0.0 END) 
        / COUNT(o.[order_id]) * 100.0, 2) AS DECIMAL(5,2))                AS [delivery_order_share_pct],
    SUM(o.[delivery_commission_sar])                                      AS [delivery_commission_sar],
    SUM(o.[contribution_sar])                                             AS [net_contribution_sar]
FROM [marts].[fact_orders] o
INNER JOIN [marts].[dim_branch] b ON o.[branch_id] = b.[branch_id]
INNER JOIN [marts].[dim_date] d ON o.[date] = d.[date]
GROUP BY b.[branch_name], d.[year_month]
ORDER BY b.[branch_name], d.[year_month];
GO

-- ------------------------------------------------------------------------------
-- 4. Channel Economics: Sales, Commission, and Net Contribution Margin
-- Grain: Sales Channel
-- ------------------------------------------------------------------------------
SELECT
    o.[channel],
    COUNT(o.[order_id])                                                    AS [order_count],
    SUM(o.[net_sales_sar])                                                AS [net_sales_sar],
    SUM(o.[delivery_commission_sar])                                      AS [delivery_commission_sar],
    SUM(o.[contribution_sar])                                             AS [contribution_sar],
    CAST(ROUND(SUM(o.[contribution_sar]) 
        / NULLIF(SUM(o.[net_sales_sar]), 0) * 100.0, 2) AS DECIMAL(5,2)) AS [contribution_margin_pct]
FROM [marts].[fact_orders] o
GROUP BY o.[channel]
ORDER BY [net_sales_sar] DESC;
GO

-- ------------------------------------------------------------------------------
-- 5. Top 10 Best-Selling Menu Items by Revenue and Gross Margin
-- Grain: Product
-- ------------------------------------------------------------------------------
SELECT TOP 10
    p.[product_id],
    p.[product_name],
    p.[category],
    SUM(l.[quantity])                                                    AS [total_units_sold],
    SUM(l.[net_sales_sar])                                               AS [net_sales_sar],
    SUM(l.[food_cost_sar])                                               AS [food_cost_sar],
    SUM(l.[net_sales_sar] - l.[food_cost_sar])                           AS [gross_profit_sar],
    CAST(ROUND((SUM(l.[net_sales_sar]) - SUM(l.[food_cost_sar])) 
        / NULLIF(SUM(l.[net_sales_sar]), 0) * 100.0, 2) AS DECIMAL(5,2)) AS [gross_margin_pct]
FROM [marts].[fact_order_lines] l
INNER JOIN [marts].[dim_product] p ON l.[product_id] = p.[product_id]
GROUP BY p.[product_id], p.[product_name], p.[category]
ORDER BY [net_sales_sar] DESC;
GO

-- ------------------------------------------------------------------------------
-- 6. Product Category Sales & Food Cost Distribution
-- Grain: Product Category
-- ------------------------------------------------------------------------------
SELECT
    p.[category],
    SUM(l.[quantity])                                                    AS [units_sold],
    SUM(l.[net_sales_sar])                                               AS [category_net_sales_sar],
    SUM(l.[food_cost_sar])                                               AS [category_food_cost_sar],
    CAST(ROUND(SUM(l.[food_cost_sar]) 
        / NULLIF(SUM(l.[net_sales_sar]), 0) * 100.0, 2) AS DECIMAL(5,2)) AS [food_cost_pct],
    CAST(ROUND(
        SUM(l.[net_sales_sar]) 
        / (SELECT SUM([net_sales_sar]) FROM [marts].[fact_order_lines]) * 100.0, 2
    ) AS DECIMAL(5,2))                                                   AS [share_of_total_sales_pct]
FROM [marts].[fact_order_lines] l
INNER JOIN [marts].[dim_product] p ON l.[product_id] = p.[product_id]
GROUP BY p.[category]
ORDER BY [category_net_sales_sar] DESC;
GO

-- ------------------------------------------------------------------------------
-- 7. Weekend vs Weekday Operating Dynamics (Saudi Calendar)
-- Grain: Weekend Indicator
-- ------------------------------------------------------------------------------
SELECT
    CASE WHEN d.[is_weekend] = 1 THEN N'Weekend (Fri/Sat)' ELSE N'Weekday (Sun-Thu)' END AS [day_type],
    COUNT(DISTINCT d.[date])                                            AS [calendar_days],
    COUNT(o.[order_id])                                                  AS [total_orders],
    CAST(ROUND(COUNT(o.[order_id]) * 1.0 / COUNT(DISTINCT d.[date]), 1) AS DECIMAL(8,1)) AS [orders_per_day],
    SUM(o.[net_sales_sar])                                              AS [net_sales_sar],
    CAST(ROUND(SUM(o.[net_sales_sar]) / COUNT(DISTINCT d.[date]), 2) AS DECIMAL(12,2))   AS [sales_per_day_sar],
    CAST(ROUND(AVG(o.[net_sales_sar]), 2) AS DECIMAL(10,2))             AS [aov_sar]
FROM [marts].[fact_orders] o
INNER JOIN [marts].[dim_date] d ON o.[date] = d.[date]
GROUP BY d.[is_weekend]
ORDER BY d.[is_weekend] DESC;
GO

-- ------------------------------------------------------------------------------
-- 8. Customer Repeat Rate & Identified vs Anonymous Orders
-- Grain: Customer Type
-- ------------------------------------------------------------------------------
SELECT
    CASE WHEN o.[customer_id] IS NULL THEN N'Anonymous Guest' ELSE N'Identified Repeat Customer' END AS [customer_segment],
    COUNT(o.[order_id])                                                  AS [order_count],
    CAST(ROUND(COUNT(o.[order_id]) * 100.0 
        / (SELECT COUNT(*) FROM [marts].[fact_orders]), 2) AS DECIMAL(5,2)) AS [share_of_orders_pct],
    SUM(o.[net_sales_sar])                                              AS [net_sales_sar],
    CAST(ROUND(AVG(o.[net_sales_sar]), 2) AS DECIMAL(10,2))             AS [aov_sar]
FROM [marts].[fact_orders] o
GROUP BY CASE WHEN o.[customer_id] IS NULL THEN N'Anonymous Guest' ELSE N'Identified Repeat Customer' END;
GO

-- ------------------------------------------------------------------------------
-- 9. Basket Composition (Lines per Order Distribution)
-- Grain: Order Line Count
-- ------------------------------------------------------------------------------
SELECT
    o.[line_count]                                                      AS [items_in_order],
    COUNT(o.[order_id])                                                  AS [order_count],
    CAST(ROUND(COUNT(o.[order_id]) * 100.0 
        / (SELECT COUNT(*) FROM [marts].[fact_orders]), 2) AS DECIMAL(5,2)) AS [pct_of_orders],
    CAST(ROUND(AVG(o.[net_sales_sar]), 2) AS DECIMAL(10,2))             AS [average_order_value_sar]
FROM [marts].[fact_orders] o
GROUP BY o.[line_count]
ORDER BY o.[line_count];
GO

-- ------------------------------------------------------------------------------
-- 10. Audit Reconciliation: Header vs Line Level Net Sales & Costs
-- Grain: Validation Check
-- ------------------------------------------------------------------------------
SELECT
    (SELECT SUM([net_sales_sar]) FROM [marts].[fact_orders])            AS [header_net_sales_sar],
    (SELECT SUM([net_sales_sar]) FROM [marts].[fact_order_lines])       AS [line_net_sales_sar],
    ABS(
        (SELECT SUM([net_sales_sar]) FROM [marts].[fact_orders]) - 
        (SELECT SUM([net_sales_sar]) FROM [marts].[fact_order_lines])
    )                                                                    AS [net_sales_variance_sar],
    (SELECT SUM([food_cost_sar]) FROM [marts].[fact_orders])            AS [header_food_cost_sar],
    (SELECT SUM([food_cost_sar]) FROM [marts].[fact_order_lines])       AS [line_food_cost_sar],
    ABS(
        (SELECT SUM([food_cost_sar]) FROM [marts].[fact_orders]) - 
        (SELECT SUM([food_cost_sar]) FROM [marts].[fact_order_lines])
    )                                                                    AS [food_cost_variance_sar];
GO
