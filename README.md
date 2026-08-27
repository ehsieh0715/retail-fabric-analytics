# Retail Sales & Inventory Analytics on Microsoft Fabric

An end-to-end analytics engineering portfolio project built with Microsoft Fabric.

## Project status

Planning and source validation in progress.

Completed functionality will be documented only after it has been implemented and verified in Microsoft Fabric.

## Business scenario

A fictional multi-store retailer needs to integrate sales, product, store, and current inventory data to monitor commercial performance and identify store-product combinations that may require inventory review.

The platform is intended to answer:

- How do revenue, units sold, and estimated profit change over time?
- Which products, categories, and stores perform best?
- How much inventory is currently held at each store?
- Which store-product combinations have low stock relative to recent sales velocity?
- Which products have high inventory but limited recent demand?
- Which items should be prioritised for replenishment review?

## Planned architecture

```text
Source CSV files
→ Microsoft Fabric Pipeline / Copy Activity
→ Bronze Delta tables
→ PySpark Silver transformations
→ Gold dimensional model
→ SQL analytics endpoint
→ Direct Lake semantic model
→ Power BI Web report
```

## Planned Gold model

- `fact_sales`
- `fact_inventory_snapshot`
- `dim_product`
- `dim_store`
- `dim_date`

The final model may change after source profiling and grain validation.

## Planned Fabric components

- OneLake
- Lakehouse
- Data Factory Pipeline
- Copy Activity
- Fabric Notebooks with PySpark
- Bronze, Silver, and Gold architecture
- Incremental and idempotent sales loading
- Data-quality checks
- Pipeline monitoring, retry, and failure handling
- SQL analytics endpoint
- Direct Lake semantic model
- DAX measures
- Power BI Web report

## Important inventory limitation

The source contains current stock on hand, not historical inventory snapshots or replenishment events.

The project will not claim to calculate:

- historical stockout events
- sales lost because of stockouts
- historical inventory movement
- exact replenishment quantities
- causal demand forecasts

Inventory outputs will be presented as current-position indicators and replenishment-review candidates.

## Repository structure

```text
.
├── data/
│   └── README.md
├── notebooks/
├── sql/
├── docs/
│   ├── architecture/
│   └── screenshots/
├── .gitignore
└── README.md
```

Folders will be populated as Fabric artifacts and verified evidence are produced.