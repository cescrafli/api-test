-- ===============================================================================
-- Script Name: queries.sql
-- Description: Verified SQL queries for extracting warehouse inventory metrics.
--              These queries handle large digits by casting them to CHAR and 
--              implement DISTINCTCOUNT logic for racking availability.
-- ===============================================================================

-- 1. Query for Daily Inventory Status
-- Casts large numeric identifiers to strings to prevent truncation in the API layer
SELECT 
    CAST(STORAGEUNIT AS CHAR) AS STORAGEUNIT,
    CAST(GR_Number AS CHAR) AS GR_Number,
    StorageBin,
    MaterialCode,
    Quantity
FROM 
    inventory_master;


-- 2. Query for Operational Metrics (Racking Available)
-- Calculates the distinct count of storage units grouped by the first two characters of the StorageBin
SELECT 
    CURRENT_DATE() AS MetricDate,
    UPPER(SUBSTRING(StorageBin, 1, 2)) AS AreaPrefix,
    COUNT(DISTINCT STORAGEUNIT) AS RackingAvailable
FROM 
    inventory_master
WHERE 
    StorageBin IS NOT NULL
GROUP BY 
    UPPER(SUBSTRING(StorageBin, 1, 2));


-- 3. Alternative Query mapping categories directly in SQL (MySQL Syntax)
-- This offloads the categorization logic to the database engine.
SELECT 
    CURRENT_DATE() AS MetricDate,
    CASE UPPER(SUBSTRING(StorageBin, 1, 2))
        WHEN 'BB' THEN 'BigBag'
        WHEN 'PM' THEN 'PM'
        WHEN 'RM' THEN 'RM'
        ELSE 'Other'
    END AS AreaCategory,
    COUNT(DISTINCT STORAGEUNIT) AS RackingAvailable
FROM 
    inventory_master
WHERE 
    StorageBin IS NOT NULL
GROUP BY 
    CASE UPPER(SUBSTRING(StorageBin, 1, 2))
        WHEN 'BB' THEN 'BigBag'
        WHEN 'PM' THEN 'PM'
        WHEN 'RM' THEN 'RM'
        ELSE 'Other'
    END;
