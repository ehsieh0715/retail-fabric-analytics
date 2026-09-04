# Silver-to-Gold Star Schema Design

## Objective

Create `nb_silver_to_gold`, a Microsoft Fabric PySpark notebook that rebuilds a compact Gold star schema from the complete, conformed Silver layer. The resulting Delta tables will support a Direct Lake semantic model while preserving the limitations of the source inventory data.

## Scope

The notebook creates five managed Delta tables:

- `dim_date`
- `dim_product`
- `dim_store`
- `fact_sales`
- `fact_inventory_position`

Recent-sales velocity, days of supply, replenishment recommendations, pipeline orchestration, semantic-model configuration, and DAX measures are outside this notebook's scope.

## Modelling decisions

The model uses the stable source business keys `product_id` and `store_id` directly. It does not add surrogate keys because the project has one source system and no slowly changing dimension history. The date dimension uses an integer `date_key` in `yyyyMMdd` format.

All Gold tables are rebuilt with Delta overwrite semantics. Each run reads the complete validated Silver state, so overwrite is simpler and more transparent than maintaining five incremental merges. Blocking checks run before each group of writes, and saved tables are read back for final reconciliation.

## Model and grain

```text
                  dim_date
                      |
                      | date_key
                      v
dim_product ---> fact_sales <--- dim_store
     |                                |
     +----> fact_inventory_position <-+
```

| Table | Grain | Key |
|---|---|---|
| `dim_date` | One row per calendar date | `date_key` |
| `dim_product` | One row per product | `product_id` |
| `dim_store` | One row per store | `store_id` |
| `fact_sales` | One row per sales transaction | `sale_id` |
| `fact_inventory_position` | One row per supplied store-product position | `store_id`, `product_id` |

An absent store-product combination remains absent. It must not be manufactured as a zero-stock position.

## Table definitions

### `dim_date`

Source: `silver_calendar`

| Column | Definition |
|---|---|
| `date_key` | Calendar date formatted as `yyyyMMdd` and cast to integer |
| `calendar_date` | Calendar date |
| `year` | Calendar year |
| `quarter_number` | Quarter number, 1 through 4 |
| `month_number` | Month number, 1 through 12 |
| `month_name` | Full English month name |
| `year_month` | Display and sorting value in `yyyy-MM` format |
| `day_of_month` | Day number within the month |
| `day_of_week_number` | ISO weekday number, Monday 1 through Sunday 7 |
| `day_name` | Full English weekday name |
| `is_weekend` | Boolean identifying Saturday or Sunday |

`month_number` is retained as the sorting column for `month_name`. A separate `quarter_name` is not created because it adds no information beyond `quarter_number`.

### `dim_product`

Source: `silver_products`

| Column | Definition |
|---|---|
| `product_id` | Product business key |
| `product_name` | Product name |
| `product_category` | Product category |
| `product_cost` | Unit product cost |
| `product_price` | Unit retail price |
| `unit_margin` | `product_price - product_cost` |
| `unit_margin_pct` | `unit_margin / product_price`; null when price is zero |

### `dim_store`

Source: `silver_stores`

| Column | Definition |
|---|---|
| `store_id` | Store business key |
| `store_name` | Store name |
| `store_city` | Store city |
| `store_location` | Store location type |
| `store_open_date` | Store opening date |

No execution-date-dependent store age is persisted.

### `fact_sales`

Sources: `silver_sales` joined to `silver_products`.

| Column | Definition |
|---|---|
| `sale_id` | Sales transaction key |
| `date_key` | Integer date key derived from `sale_date` |
| `product_id` | Product business key |
| `store_id` | Store business key |
| `units` | Units sold |
| `unit_price` | Product price applied during the Gold build |
| `unit_cost` | Product cost applied during the Gold build |
| `sales_amount` | `units * unit_price` |
| `cost_amount` | `units * unit_cost` |
| `gross_profit` | `sales_amount - cost_amount` |

Money columns use fixed-precision decimal types, not floating-point types. Persisting the applied price and cost in the fact table prevents later product-dimension updates from retroactively changing previously built sales measures.

### `fact_inventory_position`

Sources: `silver_inventory_position` joined to `silver_products`.

| Column | Definition |
|---|---|
| `store_id` | Store business key |
| `product_id` | Product business key |
| `stock_on_hand` | Recorded current stock quantity |
| `inventory_cost_value` | `stock_on_hand * product_cost` |
| `inventory_retail_value` | `stock_on_hand * product_price` |
| `source_ingested_at` | Source ingestion timestamp retained for audit context |

This table represents a current inventory position. `source_ingested_at` is not a business snapshot date, and the table must not be described as historical inventory.

## Data flow and write order

1. Read the five Silver tables.
2. Build the three dimension DataFrames.
3. Run all blocking dimension checks.
4. Overwrite `dim_date`, `dim_product`, and `dim_store` as Delta tables.
5. Build the two fact DataFrames using the validated Silver inputs.
6. Run all blocking fact and foreign-key checks.
7. Overwrite `fact_sales` and `fact_inventory_position` as Delta tables.
8. Read all five saved Gold tables back from the Lakehouse.
9. Run and display final reconciliation checks.

Dimensions are written before facts so consumers never encounter newly written facts whose required dimension tables have not yet been produced during an initial build.

## Quality controls

Blocking checks must stop execution before the affected tables are written when any of the following conditions occurs:

- a required source or output is empty;
- a dimension key is null or duplicated;
- `fact_sales.sale_id` is null or duplicated;
- a fact product, store, or date foreign key has no matching dimension row;
- `units` is null or not positive;
- `stock_on_hand` is null or negative;
- a required price, cost, or derived monetary value is null.

Products priced below cost remain a displayed business warning rather than a blocking data-quality failure.

## Expected reconciliation

| Table or measure | Expected value |
|---|---:|
| `dim_product` rows | 35 |
| `dim_store` rows | 50 |
| `dim_date` rows | 638 |
| `fact_sales` rows | 829,262 |
| Distinct `fact_sales.sale_id` | 829,262 |
| `fact_sales.units` total | 1,090,565 |
| Minimum sales date represented | 2022-01-01 |
| Maximum sales date represented | 2023-09-30 |
| `fact_inventory_position` rows | 1,593 |

Expected constants serve as reconciliation controls for this fixed portfolio dataset. Structural checks such as uniqueness, referential integrity, and valid values remain independently enforced.

## Idempotency and rerun test

Run `nb_silver_to_gold` twice without changing or reprocessing Silver. After the second run, all five row counts and the sales-unit total must remain unchanged. This demonstrates deterministic Gold reconstruction. It does not imply that Bronze Copy Activity prevents repeated ingestion of the same source file.

## Completion criteria

The notebook is complete when:

- all five Gold Delta tables are created with the documented schemas and grains;
- every blocking quality check passes on the validated project dataset;
- saved-table reconciliation matches all expected values;
- a second unchanged run produces identical row counts and totals;
- notebook output clearly distinguishes blocking failures from business warnings;
- the repository copy of the executed notebook contains sufficient outputs to document the Fabric run.
