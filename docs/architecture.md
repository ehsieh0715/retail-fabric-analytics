# Technical Architecture

This document expands the high-level architecture shown in the main README and describes the item-level data flow, orchestration boundaries, and key architectural design choices.

## Detailed End-to-End Flow

```mermaid
flowchart TB
    subgraph Local["Local data preparation"]
        direction TB

        Source["Maven Analytics source package<br/>6 source CSV files"]

        Profile["source_profile.json<br/>Structure and data-quality evidence"]

        SalesPrepared["21 monthly sales files"]

        ReferencePrepared["5 source-aligned reference files"]

        Source -.->|"profile_source.py profiles all source files"| Profile

        Source -->|"sales.csv processed by create_sales_batches.py"| SalesPrepared

        Source -->|"reference files retained as supplied"| ReferencePrepared
    end

    subgraph Fabric["Microsoft Fabric"]
        direction TB

        subgraph Landing["OneLake landing zone"]
            direction TB

            SalesLanding["sales/<br/>Monthly sales files"]

            ReferenceLanding["reference/<br/>Reference files"]
        end

        SalesLoad["pl_retail_sales_load<br/>Parameterised ingestion pipeline"]

        ReferenceLoad["pl_retail_reference_load<br/>Reference ingestion pipeline"]

        subgraph Bronze["Bronze layer"]
            direction TB

            BronzeSales["bronze_sales"]

            BronzeReference["bronze_products<br/>bronze_stores<br/>bronze_inventory<br/>bronze_calendar"]
        end

        Transform["pl_retail_transform<br/>Transformation orchestration"]

        BronzeToSilver["1 · nb_bronze_to_silver<br/>Validate, standardise, and deduplicate"]

        subgraph SilverLayer["Silver layer"]
            direction TB

            Silver["Silver Delta tables<br/>Validated, deduplicated,<br/>and conformed business data"]
        end

        SilverToGold["2 · nb_silver_to_gold<br/>Build and reconcile analytical tables"]

        subgraph GoldLayer["Gold layer"]
            direction TB

            Gold["Gold star schema<br/>Shared dimensions and two fact tables"]
        end

        Semantic["sm_retail_analytics<br/>Direct Lake semantic model and DAX"]

        Report["Retail Sales & Inventory Analytics<br/>Four-page Power BI report"]

        SQL["SQL analytics endpoint<br/>Gold reconciliation access"]

        SalesLanding -->|"read by"| SalesLoad
        ReferenceLanding -->|"operational files read by"| ReferenceLoad

        SalesLoad -->|"appends"| BronzeSales
        ReferenceLoad -->|"overwrites"| BronzeReference

        BronzeSales -->|"read by"| BronzeToSilver
        BronzeReference -->|"read by"| BronzeToSilver

        BronzeToSilver -->|"writes"| Silver
        Silver -->|"read by"| SilverToGold
        SilverToGold -->|"writes"| Gold

        Transform -.->|"activity 1"| BronzeToSilver
        Transform -.->|"activity 2 · runs after activity 1 succeeds"| SilverToGold

        Gold --> Semantic
        Semantic --> Report
        Gold -.->|"available through"| SQL
    end

    SalesPrepared -->|"uploaded to"| SalesLanding
    ReferencePrepared -->|"uploaded to"| ReferenceLanding
```

Solid arrows show the movement and transformation of data. Dashed arrows show supporting profiling, orchestration control, or validation access.

`pl_retail_transform` does not store or transform data directly. It runs `nb_bronze_to_silver` first and starts `nb_silver_to_gold` only after the first notebook activity succeeds. The notebooks read from and write to the Lakehouse layers shown by the solid data path.

The fifth reference file, `data_dictionary.csv`, remains in the landing zone as source documentation and is not loaded into a Bronze table.

## Architectural Design Choices

| Area | Design choice | Rationale |
|---|---|---|
| Local preparation | Source profiling and monthly sales-batch creation run before Fabric ingestion. | Establishes a reproducible source baseline and repeatable ingestion inputs. |
| Ingestion | Monthly sales files use parameter-driven append ingestion, while complete reference extracts overwrite their Bronze tables. | Aligns each ingestion strategy with the way its source data is delivered. |
| Medallion transformation | Bronze preserves source-aligned records and ingestion metadata. Silver validates, standardises, and deduplicates the data, while Gold deterministically rebuilds and reconciles the analytical model. | Separates traceability, data conformance, and analytical modelling into clear responsibilities. |
| Analytics | The Direct Lake semantic model queries the Gold tables and adds reusable DAX measures and disconnected report controls. | Supports flexible analysis without creating another imported copy of the analytical data. |

> [!NOTE]
> Inventory represents the latest supplied store-product position because the source does not contain historical snapshots.

## Related Documentation

- See the [main README](../README.md) for business outcomes, report pages, data modelling, and analytical definitions.
- See the [deployment guide](deployment.md) for import order, environment rebinding, and deployment validation.
- See [`validate_gold.sql`](../sql/validate_gold.sql) for independent Gold-layer reconciliation.
