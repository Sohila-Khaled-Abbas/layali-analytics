-- ==============================================================================
-- Script 04: Create Marts Dimensional Tables & Fact Tables for Layali Analytics
-- T-SQL dialect for Microsoft SQL Server
-- ==============================================================================

USE [LayaliAnalytics];
GO

-- 1. Date Dimension (Jan - Jun 2026)
IF OBJECT_ID(N'marts.dim_date', N'U') IS NULL
BEGIN
    CREATE TABLE [marts].[dim_date] (
        [date]         DATE          NOT NULL,
        [month_start]  DATE          NOT NULL,
        [year_month]   NVARCHAR(7)   NOT NULL,
        [month_sort]   INT           NOT NULL,
        [day_name]     NVARCHAR(20)  NOT NULL,
        [weekday_sort] INT           NOT NULL,
        [is_weekend]   BIT           NOT NULL,
        CONSTRAINT [PK_dim_date] PRIMARY KEY CLUSTERED ([date])
    );
END
GO

-- 2. Branch Dimension
IF OBJECT_ID(N'marts.dim_branch', N'U') IS NULL
BEGIN
    CREATE TABLE [marts].[dim_branch] (
        [branch_id]   NVARCHAR(20)  NOT NULL,
        [branch_name] NVARCHAR(100) NOT NULL,
        [opened_date] DATE          NOT NULL,
        CONSTRAINT [PK_dim_branch] PRIMARY KEY CLUSTERED ([branch_id])
    );
END
GO

-- 3. Product Dimension
IF OBJECT_ID(N'marts.dim_product', N'U') IS NULL
BEGIN
    CREATE TABLE [marts].[dim_product] (
        [product_id]     NVARCHAR(20)   NOT NULL,
        [product_name]   NVARCHAR(100)  NOT NULL,
        [category]       NVARCHAR(50)   NOT NULL,
        [unit_price_sar] DECIMAL(12, 2) NOT NULL,
        [unit_cost_sar]  DECIMAL(12, 2) NOT NULL,
        CONSTRAINT [PK_dim_product] PRIMARY KEY CLUSTERED ([product_id])
    );
END
GO

-- 4. Channel Dimension
IF OBJECT_ID(N'marts.dim_channel', N'U') IS NULL
BEGIN
    CREATE TABLE [marts].[dim_channel] (
        [channel]      NVARCHAR(50) NOT NULL,
        [channel_name] NVARCHAR(50) NOT NULL,
        CONSTRAINT [PK_dim_channel] PRIMARY KEY CLUSTERED ([channel])
    );
END
GO

-- 5. Customer Dimension
-- Anonymous customer_id remains NULL in facts; no synthetic surrogate created for anonymous orders
IF OBJECT_ID(N'marts.dim_customer', N'U') IS NULL
BEGIN
    CREATE TABLE [marts].[dim_customer] (
        [customer_id] NVARCHAR(50) NOT NULL,
        CONSTRAINT [PK_dim_customer] PRIMARY KEY CLUSTERED ([customer_id])
    );
END
GO

-- 6. Fact Orders
-- Grain: One completed order
IF OBJECT_ID(N'marts.fact_orders', N'U') IS NULL
BEGIN
    CREATE TABLE [marts].[fact_orders] (
        [order_id]                NVARCHAR(50)   NOT NULL,
        [date]                    DATE           NOT NULL,
        [order_timestamp]         DATETIME2      NOT NULL,
        [branch_id]               NVARCHAR(20)   NOT NULL,
        [channel]                 NVARCHAR(50)   NOT NULL,
        [customer_id]             NVARCHAR(50)   NULL,
        [line_count]              INT            NOT NULL,
        [net_sales_sar]           DECIMAL(12, 2) NOT NULL,
        [food_cost_sar]           DECIMAL(12, 2) NOT NULL,
        [delivery_commission_sar] DECIMAL(12, 2) NOT NULL,
        [contribution_sar]        DECIMAL(12, 2) NOT NULL,
        [batch_month]             NVARCHAR(7)    NOT NULL,
        CONSTRAINT [PK_fact_orders] PRIMARY KEY CLUSTERED ([order_id]),
        CONSTRAINT [FK_fact_orders_date] FOREIGN KEY ([date]) REFERENCES [marts].[dim_date] ([date]),
        CONSTRAINT [FK_fact_orders_branch] FOREIGN KEY ([branch_id]) REFERENCES [marts].[dim_branch] ([branch_id]),
        CONSTRAINT [FK_fact_orders_channel] FOREIGN KEY ([channel]) REFERENCES [marts].[dim_channel] ([channel]),
        CONSTRAINT [FK_fact_orders_customer] FOREIGN KEY ([customer_id]) REFERENCES [marts].[dim_customer] ([customer_id])
    );
    CREATE NONCLUSTERED INDEX [IX_fact_orders_date] ON [marts].[fact_orders] ([date]);
    CREATE NONCLUSTERED INDEX [IX_fact_orders_branch] ON [marts].[fact_orders] ([branch_id]);
    CREATE NONCLUSTERED INDEX [IX_fact_orders_channel] ON [marts].[fact_orders] ([channel]);
    CREATE NONCLUSTERED INDEX [IX_fact_orders_batch] ON [marts].[fact_orders] ([batch_month]);
END
GO

-- 7. Fact Order Lines
-- Grain: One completed order line (dimension keys copied from order; commission NOT repeated on lines)
IF OBJECT_ID(N'marts.fact_order_lines', N'U') IS NULL
BEGIN
    CREATE TABLE [marts].[fact_order_lines] (
        [order_line_id]  NVARCHAR(50)   NOT NULL,
        [order_id]       NVARCHAR(50)   NOT NULL,
        [date]           DATE           NOT NULL,
        [branch_id]      NVARCHAR(20)   NOT NULL,
        [product_id]     NVARCHAR(20)   NOT NULL,
        [channel]        NVARCHAR(50)   NOT NULL,
        [customer_id]    NVARCHAR(50)   NULL,
        [quantity]       INT            NOT NULL,
        [unit_price_sar] DECIMAL(12, 2) NOT NULL,
        [unit_cost_sar]  DECIMAL(12, 2) NOT NULL,
        [discount_sar]   DECIMAL(12, 2) NOT NULL,
        [net_sales_sar]  DECIMAL(12, 2) NOT NULL,
        [food_cost_sar]  DECIMAL(12, 2) NOT NULL,
        [batch_month]    NVARCHAR(7)    NOT NULL,
        CONSTRAINT [PK_fact_order_lines] PRIMARY KEY CLUSTERED ([order_line_id]),
        CONSTRAINT [FK_fact_lines_date] FOREIGN KEY ([date]) REFERENCES [marts].[dim_date] ([date]),
        CONSTRAINT [FK_fact_lines_branch] FOREIGN KEY ([branch_id]) REFERENCES [marts].[dim_branch] ([branch_id]),
        CONSTRAINT [FK_fact_lines_product] FOREIGN KEY ([product_id]) REFERENCES [marts].[dim_product] ([product_id]),
        CONSTRAINT [FK_fact_lines_channel] FOREIGN KEY ([channel]) REFERENCES [marts].[dim_channel] ([channel]),
        CONSTRAINT [FK_fact_lines_customer] FOREIGN KEY ([customer_id]) REFERENCES [marts].[dim_customer] ([customer_id])
    );
    CREATE NONCLUSTERED INDEX [IX_fact_lines_date] ON [marts].[fact_order_lines] ([date]);
    CREATE NONCLUSTERED INDEX [IX_fact_lines_order] ON [marts].[fact_order_lines] ([order_id]);
    CREATE NONCLUSTERED INDEX [IX_fact_lines_branch] ON [marts].[fact_order_lines] ([branch_id]);
    CREATE NONCLUSTERED INDEX [IX_fact_lines_product] ON [marts].[fact_order_lines] ([product_id]);
    CREATE NONCLUSTERED INDEX [IX_fact_lines_batch] ON [marts].[fact_order_lines] ([batch_month]);
END
GO
