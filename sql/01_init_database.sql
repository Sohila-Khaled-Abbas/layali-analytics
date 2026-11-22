-- ==============================================================================
-- Script 01: Initialize Database & Schemas for Layali Analytics
-- T-SQL dialect for Microsoft SQL Server
-- ==============================================================================

USE [master];
GO

IF NOT EXISTS (SELECT 1 FROM sys.databases WHERE name = N'LayaliAnalytics')
BEGIN
    CREATE DATABASE [LayaliAnalytics]
    COLLATE Latin1_General_100_CI_AS_SC_UTF8;
END
GO

USE [LayaliAnalytics];
GO

-- Create Raw Schema (landing zone for bulk ingestion)
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = N'raw')
BEGIN
    EXEC(N'CREATE SCHEMA [raw];');
END
GO

-- Create Staging Schema (typed, validated, and deduplicated views)
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = N'staging')
BEGIN
    EXEC(N'CREATE SCHEMA [staging];');
END
GO

-- Create Marts Schema (star schema: facts and dimensions)
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = N'marts')
BEGIN
    EXEC(N'CREATE SCHEMA [marts];');
END
GO
