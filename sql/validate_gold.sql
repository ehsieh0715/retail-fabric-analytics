-- 1. Gold row counts, totals, and date coverage
SELECT
    'fact_sales rows' AS validation_check,
    CAST(COUNT_BIG(*) AS varchar(30)) AS actual_result,
    '829262' AS expected_result
FROM dbo.fact_sales

UNION ALL

SELECT
    'distinct sale_id values',
    CAST(COUNT_BIG(DISTINCT sale_id) AS varchar(30)),
    '829262'
FROM dbo.fact_sales

UNION ALL

SELECT
    'total units',
    CAST(SUM(CAST(units AS bigint)) AS varchar(30)),
    '1090565'
FROM dbo.fact_sales

UNION ALL

SELECT
    'fact_inventory_position rows',
    CAST(COUNT_BIG(*) AS varchar(30)),
    '1593'
FROM dbo.fact_inventory_position

UNION ALL

SELECT
    'dim_product rows',
    CAST(COUNT_BIG(*) AS varchar(30)),
    '35'
FROM dbo.dim_product

UNION ALL

SELECT
    'dim_store rows',
    CAST(COUNT_BIG(*) AS varchar(30)),
    '50'
FROM dbo.dim_store

UNION ALL

SELECT
    'dim_date rows',
    CAST(COUNT_BIG(*) AS varchar(30)),
    '638'
FROM dbo.dim_date

UNION ALL

SELECT
    'minimum sales date',
    CONVERT(varchar(10), MIN(d.calendar_date), 23),
    '2022-01-01'
FROM dbo.fact_sales AS f
INNER JOIN dbo.dim_date AS d
    ON d.date_key = f.date_key

UNION ALL

SELECT
    'maximum sales date',
    CONVERT(varchar(10), MAX(d.calendar_date), 23),
    '2023-09-30'
FROM dbo.fact_sales AS f
INNER JOIN dbo.dim_date AS d
    ON d.date_key = f.date_key;


-- 2. Sales foreign-key coverage
SELECT
    SUM(CASE WHEN p.product_id IS NULL THEN 1 ELSE 0 END)
        AS orphan_sales_products,
    SUM(CASE WHEN s.store_id IS NULL THEN 1 ELSE 0 END)
        AS orphan_sales_stores,
    SUM(CASE WHEN d.date_key IS NULL THEN 1 ELSE 0 END)
        AS orphan_sales_dates
FROM dbo.fact_sales AS f
LEFT JOIN dbo.dim_product AS p
    ON p.product_id = f.product_id
LEFT JOIN dbo.dim_store AS s
    ON s.store_id = f.store_id
LEFT JOIN dbo.dim_date AS d
    ON d.date_key = f.date_key;


-- 3. Inventory foreign-key coverage
SELECT
    SUM(CASE WHEN p.product_id IS NULL THEN 1 ELSE 0 END)
        AS orphan_inventory_products,
    SUM(CASE WHEN s.store_id IS NULL THEN 1 ELSE 0 END)
        AS orphan_inventory_stores
FROM dbo.fact_inventory_position AS i
LEFT JOIN dbo.dim_product AS p
    ON p.product_id = i.product_id
LEFT JOIN dbo.dim_store AS s
    ON s.store_id = i.store_id;