-- ==============================================================================
-- Script 03: Create Staging Views for Layali Analytics
-- Explicit casts, key checks, and deterministic deduplication of exact duplicates.
-- Does NOT silently repair unknown keys or impossible discounts.
-- Partitions by (batch_month, order_id) to match clustered indexes.
-- ==============================================================================

USE [LayaliAnalytics];
GO

-- 1. Staging Branches
CREATE OR ALTER VIEW [staging].[stg_branches]
AS
SELECT
    CAST([branch_id] AS NVARCHAR(20))   AS [branch_id],
    CAST([branch_name] AS NVARCHAR(100)) AS [branch_name],
    CAST([opened_date] AS DATE)         AS [opened_date],
    [source_file],
    [loaded_at]
FROM [raw].[branches];
GO

-- 2. Staging Products
CREATE OR ALTER VIEW [staging].[stg_products]
AS
SELECT
    CAST([product_id] AS NVARCHAR(20))       AS [product_id],
    CAST([product_name] AS NVARCHAR(100))    AS [product_name],
    CAST([category] AS NVARCHAR(50))         AS [category],
    CAST([unit_price_sar] AS DECIMAL(12, 2)) AS [unit_price_sar],
    CAST([unit_cost_sar] AS DECIMAL(12, 2))  AS [unit_cost_sar],
    [source_file],
    [loaded_at]
FROM [raw].[products];
GO

-- 3. Staging Customers
CREATE OR ALTER VIEW [staging].[stg_customers]
AS
SELECT DISTINCT
    CAST([customer_id] AS NVARCHAR(50)) AS [customer_id],
    [source_file],
    [loaded_at]
FROM [raw].[customers]
WHERE [customer_id] IS NOT NULL AND LTRIM(RTRIM([customer_id])) <> '';
GO

-- 4. Staging Orders
-- Deterministic deduplication of exact duplicate source rows based on order_id within batch
CREATE OR ALTER VIEW [staging].[stg_orders]
AS
WITH DeduplicatedOrders AS (
    SELECT
        [order_id],
        [order_timestamp],
        [order_date],
        [branch_id],
        [channel],
        [customer_id],
        [status],
        [delivery_commission_sar],
        [source_file],
        [batch_month],
        [loaded_at],
        ROW_NUMBER() OVER (
            PARTITION BY [batch_month], [order_id]
            ORDER BY [loaded_at] ASC
        ) AS [row_num]
    FROM [raw].[orders]
)
SELECT
    CAST(o.[order_id] AS NVARCHAR(50))                              AS [order_id],
    CAST(o.[order_timestamp] AS DATETIME2)                         AS [order_timestamp],
    CAST(o.[order_date] AS DATE)                                   AS [order_date],
    CAST(o.[branch_id] AS NVARCHAR(20))                            AS [branch_id],
    CAST(o.[channel] AS NVARCHAR(50))                              AS [channel],
    CAST(NULLIF(LTRIM(RTRIM(o.[customer_id])), '') AS NVARCHAR(50)) AS [customer_id],
    CAST(o.[status] AS NVARCHAR(50))                               AS [status],
    CAST(o.[delivery_commission_sar] AS DECIMAL(12, 2))            AS [delivery_commission_sar],
    o.[batch_month],
    o.[source_file],
    o.[loaded_at],
    -- Key checks (exposed without modifying raw data)
    CAST(CASE WHEN b.[branch_id] IS NOT NULL THEN 1 ELSE 0 END AS BIT) AS [is_valid_branch],
    CAST(CASE WHEN o.[channel] IN ('dine-in', 'takeaway', 'delivery') THEN 1 ELSE 0 END AS BIT) AS [is_valid_channel],
    CAST(CASE WHEN o.[status] IN ('completed', 'cancelled') THEN 1 ELSE 0 END AS BIT) AS [is_valid_status]
FROM DeduplicatedOrders o
LEFT JOIN [raw].[branches] b ON o.[branch_id] = b.[branch_id]
WHERE o.[row_num] = 1;
GO

-- 5. Staging Order Lines
-- Deterministic deduplication of exact duplicate lines based on order_line_id within batch
CREATE OR ALTER VIEW [staging].[stg_order_lines]
AS
WITH DeduplicatedLines AS (
    SELECT
        [order_line_id],
        [order_id],
        [product_id],
        [quantity],
        [unit_price_sar],
        [unit_cost_sar],
        [discount_sar],
        [source_file],
        [batch_month],
        [loaded_at],
        ROW_NUMBER() OVER (
            PARTITION BY [batch_month], [order_line_id]
            ORDER BY [loaded_at] ASC
        ) AS [row_num]
    FROM [raw].[order_lines]
)
SELECT
    CAST(l.[order_line_id] AS NVARCHAR(50))   AS [order_line_id],
    CAST(l.[order_id] AS NVARCHAR(50))        AS [order_id],
    CAST(l.[product_id] AS NVARCHAR(20))      AS [product_id],
    CAST(l.[quantity] AS INT)                 AS [quantity],
    CAST(l.[unit_price_sar] AS DECIMAL(12,2)) AS [unit_price_sar],
    CAST(l.[unit_cost_sar] AS DECIMAL(12,2))  AS [unit_cost_sar],
    CAST(l.[discount_sar] AS DECIMAL(12,2))   AS [discount_sar],
    -- Calculations preserving raw discount integrity without silent capping
    CAST(CAST(l.[quantity] AS INT) * CAST(l.[unit_price_sar] AS DECIMAL(12,2)) AS DECIMAL(12,2)) AS [gross_sar],
    CAST((CAST(l.[quantity] AS INT) * CAST(l.[unit_price_sar] AS DECIMAL(12,2))) - CAST(l.[discount_sar] AS DECIMAL(12,2)) AS DECIMAL(12,2)) AS [net_sales_sar],
    CAST(CAST(l.[quantity] AS INT) * CAST(l.[unit_cost_sar] AS DECIMAL(12,2)) AS DECIMAL(12,2)) AS [food_cost_sar],
    l.[batch_month],
    l.[source_file],
    l.[loaded_at],
    -- Key and discount integrity checks
    CAST(CASE WHEN p.[product_id] IS NOT NULL THEN 1 ELSE 0 END AS BIT) AS [is_valid_product],
    CAST(CASE
        WHEN CAST(l.[discount_sar] AS DECIMAL(12,2)) >= 0
             AND CAST(l.[discount_sar] AS DECIMAL(12,2)) <= (CAST(l.[quantity] AS INT) * CAST(l.[unit_price_sar] AS DECIMAL(12,2)))
        THEN 1 ELSE 0
    END AS BIT) AS [is_valid_discount]
FROM DeduplicatedLines l
LEFT JOIN [raw].[products] p ON l.[product_id] = p.[product_id]
WHERE l.[row_num] = 1;
GO
