-- ==============================================================================
-- Script 05: Populate marts.dim_date (Jan 1, 2026 - Jun 30, 2026)
-- Uses pure T-SQL date functions: DATEFROMPARTS, DATEADD, DATEDIFF, DATENAME
-- ==============================================================================

USE [LayaliAnalytics];
GO

SET NOCOUNT ON;

DECLARE @StartDate DATE = DATEFROMPARTS(2026, 1, 1);
DECLARE @EndDate   DATE = DATEFROMPARTS(2026, 6, 30);

;WITH DateSequence AS (
    SELECT @StartDate AS [cal_date]
    UNION ALL
    SELECT DATEADD(DAY, 1, [cal_date])
    FROM DateSequence
    WHERE [cal_date] < @EndDate
)
MERGE INTO [marts].[dim_date] AS target
USING (
    SELECT
        [cal_date]                                                        AS [date],
        DATEFROMPARTS(YEAR([cal_date]), MONTH([cal_date]), 1)             AS [month_start],
        CONCAT(
            CAST(YEAR([cal_date]) AS NVARCHAR(4)),
            N'-',
            RIGHT(CONCAT(N'0', CAST(MONTH([cal_date]) AS NVARCHAR(2))), 2)
        )                                                                 AS [year_month],
        (YEAR([cal_date]) * 100) + MONTH([cal_date])                      AS [month_sort],
        DATENAME(WEEKDAY, [cal_date])                                     AS [day_name],
        -- In Saudi Arabia, week starts Sunday (1) through Saturday (7)
        ((DATEPART(WEEKDAY, [cal_date]) + @@DATEFIRST - 1) % 7) + 1       AS [weekday_sort],
        -- Weekend in Saudi Arabia: Friday and Saturday
        CASE 
            WHEN DATENAME(WEEKDAY, [cal_date]) IN (N'Friday', N'Saturday') THEN 1 
            ELSE 0 
        END                                                               AS [is_weekend]
    FROM DateSequence
) AS source
ON target.[date] = source.[date]
WHEN MATCHED THEN
    UPDATE SET
        target.[month_start]  = source.[month_start],
        target.[year_month]   = source.[year_month],
        target.[month_sort]   = source.[month_sort],
        target.[day_name]     = source.[day_name],
        target.[weekday_sort] = source.[weekday_sort],
        target.[is_weekend]   = source.[is_weekend]
WHEN NOT MATCHED THEN
    INSERT ([date], [month_start], [year_month], [month_sort], [day_name], [weekday_sort], [is_weekend])
    VALUES (source.[date], source.[month_start], source.[year_month], source.[month_sort], source.[day_name], source.[weekday_sort], source.[is_weekend])
OPTION (MAXRECURSION 500);
GO
