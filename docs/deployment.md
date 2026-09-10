# Rebuilding the Solution in Microsoft Fabric

This guide explains how to recreate the Fabric implementation in a new workspace using locally prepared source files and the exported Fabric item definitions stored in this repository.

It covers Fabric deployment only. Complete [Step 1: Prepare the Source Files Locally](../README.md#1-prepare-the-source-files-locally) before following this guide.

## Prerequisites

The deployment requires:

- access to an active Microsoft Fabric capacity
- permission to create and run Lakehouse, pipeline, notebook, semantic-model, and report items
- 21 prepared monthly sales files and five complete reference files
- Python 3 and [Microsoft Fabric CLI](https://microsoft.github.io/fabric-cli/)
- Bash or Zsh for running the command examples

Run all commands from the repository root so that the relative paths resolve correctly.

The examples were prepared using Fabric CLI version 1.7.0:

```bash
python3 -m pip install ms-fabric-cli==1.7.0
fab auth login
fab auth status
```

Set the target workspace name:

```bash
FABRIC_WORKSPACE="YOUR_WORKSPACE_NAME"
```

Replace `YOUR_WORKSPACE_NAME` with the display name of a Fabric-enabled workspace. Keep the quotes if the name contains spaces.

## Deployment Assets

The repository contains the following Fabric item definitions:

| Item | Repository path |
|---|---|
| Bronze-to-Silver notebook | `fabric/notebooks/nb_bronze_to_silver.Notebook/` |
| Silver-to-Gold notebook | `fabric/notebooks/nb_silver_to_gold.Notebook/` |
| Sales ingestion pipeline | `fabric/pipelines/pl_retail_sales_load.DataPipeline/` |
| Reference ingestion pipeline | `fabric/pipelines/pl_retail_reference_load.DataPipeline/` |
| Transformation pipeline | `fabric/pipelines/pl_retail_transform.DataPipeline/` |
| Direct Lake semantic model | `fabric/semantic-model/sm_retail_analytics.SemanticModel/` |
| Power BI report | `fabric/report/Retail Sales & Inventory Analytics.Report/` |

The repository does not contain the deployed Lakehouse or its persisted data. These are recreated by uploading the prepared source files and running the ingestion and transformation processes.

## Deployment Sequence

Rebuild the solution in the following dependency order:

1. Create the target workspace and `lh_retail_analytics` Lakehouse.
2. Upload the prepared sales and reference files to the OneLake landing zone.
3. Import and run the ingestion pipelines to create the Bronze tables.
4. Import the transformation notebooks and orchestration pipeline, then build the Silver and Gold layers.
5. Import and initialise the Direct Lake semantic model, resolve the target semantic-model binding, and import the Power BI report.

## Deploy the Solution

### 1. Set Up the Target Workspace and Lakehouse

Create or select a workspace backed by an active Microsoft Fabric capacity. The deploying user must have permission to create and run Lakehouse, Data Factory, notebook, semantic-model, and report items in that workspace.

Workspace creation and capacity assignment are completed in the Fabric portal because the available capacity and permissions depend on the target tenant.

Confirm that the Fabric CLI can access the target workspace:

```bash
fab exists "${FABRIC_WORKSPACE}.Workspace"
```

Create the target Lakehouse:

```bash
fab mkdir \
  "${FABRIC_WORKSPACE}.Workspace/lh_retail_analytics.Lakehouse"
```

Confirm that the Lakehouse exists:

```bash
fab exists \
  "${FABRIC_WORKSPACE}.Workspace/lh_retail_analytics.Lakehouse"
```

### 2. Upload the Landing Files

Create each landing folder in order because `fab mkdir` does not
recursively create missing parent directories:

```bash
fab mkdir \
  "${FABRIC_WORKSPACE}.Workspace/lh_retail_analytics.Lakehouse/Files/landing"

fab mkdir \
  "${FABRIC_WORKSPACE}.Workspace/lh_retail_analytics.Lakehouse/Files/landing/maven_toys"

fab mkdir \
  "${FABRIC_WORKSPACE}.Workspace/lh_retail_analytics.Lakehouse/Files/landing/maven_toys/reference"

fab mkdir \
  "${FABRIC_WORKSPACE}.Workspace/lh_retail_analytics.Lakehouse/Files/landing/maven_toys/sales"
```

Confirm that both target folders are available:

```bash
fab ls \
  "${FABRIC_WORKSPACE}.Workspace/lh_retail_analytics.Lakehouse/Files/landing/maven_toys"
```

The result should include:

```text
reference
sales
```

Upload the five complete reference files:

```bash
for file_name in products.csv stores.csv inventory.csv calendar.csv data_dictionary.csv; do
  fab cp \
    "data/raw/maven_toys/${file_name}" \
    "${FABRIC_WORKSPACE}.Workspace/lh_retail_analytics.Lakehouse/Files/landing/maven_toys/reference/${file_name}"
done
```

Upload the monthly sales batches:

```bash
for batch_path in data/raw/maven_toys/load_batches/sales_*.csv; do
  batch_name="$(basename "${batch_path}")"

  fab cp \
    "${batch_path}" \
    "${FABRIC_WORKSPACE}.Workspace/lh_retail_analytics.Lakehouse/Files/landing/maven_toys/sales/${batch_name}"
done
```

Confirm the uploaded files:

```bash
fab ls \
  "${FABRIC_WORKSPACE}.Workspace/lh_retail_analytics.Lakehouse/Files/landing/maven_toys/reference"

fab ls \
  "${FABRIC_WORKSPACE}.Workspace/lh_retail_analytics.Lakehouse/Files/landing/maven_toys/sales"
```

The data dictionary remains in Landing as source documentation. It is not loaded into a Bronze table.

### 3. Load the Bronze Layer

Prepare a target-specific deployment copy:

```bash
python3 scripts/prepare_fabric_deployment.py initialize \
  --workspace "${FABRIC_WORKSPACE}"
```

This creates `.deployment/fabric/` and resolves the target workspace and
Lakehouse bindings. Later steps add bindings for items that do not exist
yet.

Import the ingestion pipelines from the deployment copy:

```bash
fab import \
  "${FABRIC_WORKSPACE}.Workspace/pl_retail_reference_load.DataPipeline" \
  -i ".deployment/fabric/pipelines/pl_retail_reference_load.DataPipeline"

fab import \
  "${FABRIC_WORKSPACE}.Workspace/pl_retail_sales_load.DataPipeline" \
  -i ".deployment/fabric/pipelines/pl_retail_sales_load.DataPipeline"
```

Run the reference load once:

```bash
fab job run \
  "${FABRIC_WORKSPACE}.Workspace/pl_retail_reference_load.DataPipeline" \
  --timeout 1800
```

Run each monthly sales batch:

```bash
for batch_path in data/raw/maven_toys/load_batches/sales_*.csv; do
  file_name=$(basename "${batch_path}")

  fab job run \
    "${FABRIC_WORKSPACE}.Workspace/pl_retail_sales_load.DataPipeline" \
    -P "sales_file_pattern:string=${file_name}" \
    --timeout 1800
done
```

Because Bronze uses append semantics, avoid rerunning a monthly file
unnecessarily. Duplicate `sale_id` values are removed in Silver, but
repeated Bronze ingestion still increases storage and processing.

After ingestion, the Bronze layer should contain:

```text
bronze_sales
bronze_products
bronze_stores
bronze_inventory
bronze_calendar
```

### 4. Build the Silver and Gold Layers

Import the two prepared notebooks:

```bash
fab import \
  "${FABRIC_WORKSPACE}.Workspace/nb_bronze_to_silver.Notebook" \
  -i ".deployment/fabric/notebooks/nb_bronze_to_silver.Notebook"

fab import \
  "${FABRIC_WORKSPACE}.Workspace/nb_silver_to_gold.Notebook" \
  -i ".deployment/fabric/notebooks/nb_silver_to_gold.Notebook"
```

Their default-Lakehouse metadata was resolved during `initialize`, so
both notebooks are already bound to the target `lh_retail_analytics`
Lakehouse.

After the notebooks have been imported, resolve their newly assigned
item IDs in the transformation-pipeline definition:

```bash
python3 scripts/prepare_fabric_deployment.py bind-notebooks \
  --workspace "${FABRIC_WORKSPACE}"
```

Import the prepared orchestration pipeline:

```bash
fab import \
  "${FABRIC_WORKSPACE}.Workspace/pl_retail_transform.DataPipeline" \
  -i ".deployment/fabric/pipelines/pl_retail_transform.DataPipeline"
```

The prepared pipeline references the two notebooks in the target
workspace. Its success dependency ensures that `nb_silver_to_gold` runs
only after `nb_bronze_to_silver` completes successfully.

Run the transformation pipeline:

```bash
fab job run \
  "${FABRIC_WORKSPACE}.Workspace/pl_retail_transform.DataPipeline" \
  --timeout 3600
```

The pipeline validates and conforms Bronze data into Silver before
rebuilding the Gold fact and dimension tables. Expected Gold row counts
and integrity checks are listed in
[Validate the Deployment](#validate-the-deployment).

### 5. Deploy the Semantic Model and Report

After the Gold tables have been created, import the prepared Direct Lake
semantic model:

```bash
fab import \
  "${FABRIC_WORKSPACE}.Workspace/sm_retail_analytics.SemanticModel" \
  -i ".deployment/fabric/semantic-model/sm_retail_analytics.SemanticModel"
```

Open the imported semantic model in Fabric and enter **Edit** mode.

The calculated helper tables may initially remain unprocessed after the
model definition is imported. To initialise them, select `_Measures` and
temporarily change its calculated-table expression from:

```dax
_Measures =
DATATABLE (
    "_Placeholder", INTEGER,
    {
        { 1 }
    }
)
```

to use `{ 2 }`, then apply the change. Restore the value to `{ 1 }` and
apply it again so that the deployed definition matches the
source-controlled model. This forces Fabric to recalculate the model's
calculated partitions.

Select **Refresh** and wait for the operation to complete. Confirm that
both the Direct Lake tables and calculated helper tables load without
red warning indicators before deploying the report.

This recalculation is required only during the initial definition-based
deployment.

Resolve the new semantic-model item ID in the report definition:

```bash
python3 scripts/prepare_fabric_deployment.py bind-report \
  --workspace "${FABRIC_WORKSPACE}"
```

Confirm that all environment-specific placeholders have been resolved:

```bash
python3 scripts/prepare_fabric_deployment.py validate
```

The command exits with an error and identifies the affected files if any
placeholder remains.

Import the prepared report:

```bash
fab import \
  "${FABRIC_WORKSPACE}.Workspace/Retail Sales & Inventory Analytics.Report" \
  -i ".deployment/fabric/report/Retail Sales & Inventory Analytics.Report"
```

The prepared report is already bound to the semantic model created in
the target workspace, so no manual report rebinding is required.

Semantic-model relationships, measures, disconnected controls, and
report behaviour are verified in
[Validate the Deployment](#validate-the-deployment).

## Validate the Deployment

A successful pipeline run already performs blocking checks and persisted-table reconciliation. Use the following checks as an independent deployment review.

### Fabric Items

Confirm that the expected items exist:

```bash
fab exists "${FABRIC_WORKSPACE}.Workspace/lh_retail_analytics.Lakehouse"
fab exists "${FABRIC_WORKSPACE}.Workspace/pl_retail_sales_load.DataPipeline"
fab exists "${FABRIC_WORKSPACE}.Workspace/pl_retail_reference_load.DataPipeline"
fab exists "${FABRIC_WORKSPACE}.Workspace/pl_retail_transform.DataPipeline"
fab exists "${FABRIC_WORKSPACE}.Workspace/nb_bronze_to_silver.Notebook"
fab exists "${FABRIC_WORKSPACE}.Workspace/nb_silver_to_gold.Notebook"
fab exists "${FABRIC_WORKSPACE}.Workspace/sm_retail_analytics.SemanticModel"
fab exists "${FABRIC_WORKSPACE}.Workspace/Retail Sales & Inventory Analytics.Report"
```

### Gold Data

Run [`sql/validate_gold.sql`](../sql/validate_gold.sql) through the Lakehouse SQL analytics endpoint. For a complete rebuild from the supplied source, all actual values should match the expected values and all orphan counts should return zero.

The transformation notebooks perform the same core integrity checks during execution; this SQL script provides an independent post-deployment review of the persisted Gold tables.

### Semantic Model and Report

Confirm that:

- the Direct Lake model can query all five Gold tables
- `Report Date` and `Analysis Period` remain disconnected
- all four report pages render without visual errors
- Day, 7 Days, and 30 Days produce the intended comparison periods
- City, Store, and Product Category filters affect the intended visuals
- inventory indicators remain based on the latest inventory position
- selecting a store displays its twelve-week revenue trend
- KPI values update consistently when the Report Date and Analysis Period selections change

## Portability Notes

The source-controlled Fabric definitions use placeholders instead of
environment-specific IDs. `prepare_fabric_deployment.py` resolves these
placeholders in the ignored `.deployment/fabric/` copy as each dependency
becomes available, leaving the original exports unchanged.

- Source CSV files and persisted OneLake data are not included in the repository.
- Fabric capacity, permissions, credentials, and tenant settings must be configured separately.
- The semantic model requires the one-time calculated-table initialisation described in Step 5.
- Sales ingestion has no processed-file ledger; a production deployment should add a watermark or ingestion-control table.
- Inventory reporting represents one current position because historical snapshots are unavailable.

## References

- [Fabric CLI import command](https://microsoft.github.io/fabric-cli/commands/fs/import/)
- [Fabric CLI OneLake operations](https://microsoft.github.io/fabric-cli/examples/onelake_examples/)
- [Fabric CLI item-management examples](https://microsoft.github.io/fabric-cli/examples/item_examples/)
