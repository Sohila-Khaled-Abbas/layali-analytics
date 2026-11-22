-- ==============================================================================
-- Script 02: Create Raw Tables for Layali Analytics
-- Preserves raw rows, source_file, and batch_month metadata
-- Clustered indexes on (batch_month, ...) optimize memory grants & partition elimination
-- ==============================================================================

USE [LayaliAnalytics];
GO

-- 1. Raw Branches
IF OBJECT_ID(N'raw.branches', N'U') IS NOT NULL DROP TABLE [raw].[branches];
CREATE TABLE [raw].[branches] (
    [branch_id]     NVARCHAR(20)  NOT NULL,
    [branch_name]   NVARCHAR(100) NOT NULL,
    [opened_date]   NVARCHAR(20)  NOT NULL,
    [source_file]   NVARCHAR(255) NOT NULL,
    [loaded_at]     DATETIME2     NOT NULL DEFAULT SYSDATETIME()
);
CREATE CLUSTERED INDEX [CIX_raw_branches] ON [raw].[branches] ([branch_id]);
GO

-- 2. Raw Products
IF OBJECT_ID(N'raw.products', N'U') IS NOT NULL DROP TABLE [raw].[products];
CREATE TABLE [raw].[products] (
    [product_id]     NVARCHAR(20)  NOT NULL,
    [product_name]   NVARCHAR(100) NOT NULL,
    [category]       NVARCHAR(50)  NOT NULL,
    [unit_price_sar] NVARCHAR(50)  NOT NULL,
    [unit_cost_sar]  NVARCHAR(50)  NOT NULL,
    [source_file]    NVARCHAR(255) NOT NULL,
    [loaded_at]      DATETIME2     NOT NULL DEFAULT SYSDATETIME()
);
CREATE CLUSTERED INDEX [CIX_raw_products] ON [raw].[products] ([product_id]);
GO

-- 3. Raw Customers
IF OBJECT_ID(N'raw.customers', N'U') IS NOT NULL DROP TABLE [raw].[customers];
CREATE TABLE [raw].[customers] (
    [customer_id]   NVARCHAR(50)  NOT NULL,
    [source_file]   NVARCHAR(255) NOT NULL,
    [loaded_at]     DATETIME2     NOT NULL DEFAULT SYSDATETIME()
);
CREATE CLUSTERED INDEX [CIX_raw_customers] ON [raw].[customers] ([customer_id]);
GO

-- 4. Raw Orders
IF OBJECT_ID(N'raw.orders', N'U') IS NOT NULL DROP TABLE [raw].[orders];
CREATE TABLE [raw].[orders] (
    [order_id]                NVARCHAR(50)  NOT NULL,
    [order_timestamp]         NVARCHAR(50)  NOT NULL,
    [order_date]              NVARCHAR(20)  NOT NULL,
    [branch_id]               NVARCHAR(20)  NOT NULL,
    [channel]                 NVARCHAR(50)  NOT NULL,
    [customer_id]             NVARCHAR(50)  NULL,
    [status]                  NVARCHAR(50)  NOT NULL,
    [delivery_commission_sar] NVARCHAR(50)  NOT NULL,
    [source_file]             NVARCHAR(255) NOT NULL,
    [batch_month]             NVARCHAR(7)   NOT NULL,
    [loaded_at]               DATETIME2     NOT NULL DEFAULT SYSDATETIME()
);
CREATE CLUSTERED INDEX [CIX_raw_orders] ON [raw].[orders] ([batch_month], [order_id]);
CREATE NONCLUSTERED INDEX [IX_raw_orders_status] ON [raw].[orders] ([status]) INCLUDE ([branch_id], [channel], [customer_id], [order_date]);
GO

-- 5. Raw Order Lines
IF OBJECT_ID(N'raw.order_lines', N'U') IS NOT NULL DROP TABLE [raw].[order_lines];
CREATE TABLE [raw].[order_lines] (
    [order_line_id]   NVARCHAR(50)  NOT NULL,
    [order_id]        NVARCHAR(50)  NOT NULL,
    [product_id]      NVARCHAR(20)  NOT NULL,
    [quantity]        NVARCHAR(20)  NOT NULL,
    [unit_price_sar]  NVARCHAR(50)  NOT NULL,
    [unit_cost_sar]   NVARCHAR(50)  NOT NULL,
    [discount_sar]    NVARCHAR(50)  NOT NULL,
    [source_file]     NVARCHAR(255) NOT NULL,
    [batch_month]     NVARCHAR(7)   NOT NULL,
    [loaded_at]       DATETIME2     NOT NULL DEFAULT SYSDATETIME()
);
CREATE CLUSTERED INDEX [CIX_raw_order_lines] ON [raw].[order_lines] ([batch_month], [order_id], [order_line_id]);
CREATE NONCLUSTERED INDEX [IX_raw_order_lines_product] ON [raw].[order_lines] ([product_id]);
GO
