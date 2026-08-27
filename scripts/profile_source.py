"""Profile the Maven Toys source CSV files.

Run from the repository root:

    python scripts/profile_source.py
"""

import json
from pathlib import Path

import pandas as pd


DATA_DIR = Path("data/raw/maven_toys")
OUTPUT_FILE = Path("reports/source_profile.json")

# Natural keys confirmed during source assessment.
# These rules are defined by us rather than inferred from the source data.
KEY_COLUMNS = {
    "sales": ["Sale_ID"],
    "products": ["Product_ID"],
    "stores": ["Store_ID"],
    "inventory": ["Store_ID", "Product_ID"],
    "calendar": ["Date"],
    "data_dictionary": ["Table", "Field"],
}


def load_sources():
    """Load all original CSV files while preserving IDs as text."""

    sources = {}

    for source_name in KEY_COLUMNS:
        file_path = DATA_DIR / f"{source_name}.csv"

        sources[source_name] = pd.read_csv(
            file_path,
            dtype="string",
            keep_default_na=False,
        )

    return sources


def profile_file(df, key_columns):
    """Return row, column, blank-value, and duplicate-key statistics."""

    blank_values = {}

    for column in df.columns:
        blank_values[column] = int(
            df[column].str.strip().eq("").sum()
        )

    return {
        "row_count": int(len(df)),
        "columns": df.columns.tolist(),
        "natural_key": key_columns,
        "blank_values": blank_values,
        "duplicate_key_rows": int(
            df.duplicated(
                subset=key_columns,
                keep="first",
            ).sum()
        ),
    }


def clean_currency(series):
    """Convert currency text such as '$9.99 ' into numeric values."""

    cleaned = (
        series
        .str.replace("$", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.strip()
    )

    return pd.to_numeric(cleaned, errors="coerce")


def build_report(sources):
    """Build structural, relationship, and business-rule checks."""

    sales = sources["sales"]
    products = sources["products"]
    stores = sources["stores"]
    inventory = sources["inventory"]
    calendar = sources["calendar"]

    # Convert source fields only inside the profiling process.
    sales_dates = pd.to_datetime(
        sales["Date"],
        format="%Y-%m-%d",
        errors="coerce",
    )
    calendar_dates = pd.to_datetime(
        calendar["Date"],
        format="%m/%d/%Y",
        errors="coerce",
    )
    units = pd.to_numeric(
        sales["Units"],
        errors="coerce",
    )
    stock = pd.to_numeric(
        inventory["Stock_On_Hand"],
        errors="coerce",
    )
    product_cost = clean_currency(products["Product_Cost"])
    product_price = clean_currency(products["Product_Price"])

    product_ids = set(products["Product_ID"])
    store_ids = set(stores["Store_ID"])

    # Determine which store-product combinations are represented
    # without assuming that an absent inventory row means zero stock.
    expected_inventory = pd.MultiIndex.from_product(
        [sorted(store_ids), sorted(product_ids)]
    )
    available_inventory = pd.MultiIndex.from_frame(
        inventory[["Store_ID", "Product_ID"]]
    )
    missing_inventory = expected_inventory.difference(
        available_inventory
    )

    file_profiles = {}

    for source_name, df in sources.items():
        file_profiles[source_name] = profile_file(
            df=df,
            key_columns=KEY_COLUMNS[source_name],
        )

    return {
        "dataset": "Maven Analytics Mexico Toy Sales",
        "files": file_profiles,
        "sales_checks": {
            "date_min": sales_dates.min().date().isoformat(),
            "date_max": sales_dates.max().date().isoformat(),
            "distinct_dates": int(sales_dates.nunique()),
            "invalid_dates": int(sales_dates.isna().sum()),
            "dates_missing_from_calendar": int(
                len(
                    set(sales_dates.dropna())
                    - set(calendar_dates.dropna())
                )
            ),
            "total_units": int(units.sum()),
            "units_min": int(units.min()),
            "units_max": int(units.max()),
            "non_positive_units": int(units.le(0).sum()),
            "orphan_product_keys": int(
                (~sales["Product_ID"].isin(product_ids)).sum()
            ),
            "orphan_store_keys": int(
                (~sales["Store_ID"].isin(store_ids)).sum()
            ),
        },
        "product_checks": {
            "invalid_cost_values": int(product_cost.isna().sum()),
            "invalid_price_values": int(product_price.isna().sum()),
            "cost_min": float(product_cost.min()),
            "cost_max": float(product_cost.max()),
            "price_min": float(product_price.min()),
            "price_max": float(product_price.max()),
            "price_below_cost_records": int(
                product_price.lt(product_cost).sum()
            ),
        },
        "inventory_checks": {
            "expected_store_product_combinations": int(
                len(expected_inventory)
            ),
            "available_store_product_combinations": int(
                len(available_inventory)
            ),
            "missing_store_product_combinations": int(
                len(missing_inventory)
            ),
            "explicit_zero_stock_records": int(stock.eq(0).sum()),
            "negative_stock_records": int(stock.lt(0).sum()),
            "total_stock_on_hand": int(stock.sum()),
            "orphan_product_keys": int(
                (~inventory["Product_ID"].isin(product_ids)).sum()
            ),
            "orphan_store_keys": int(
                (~inventory["Store_ID"].isin(store_ids)).sum()
            ),
        },
        "interpretation_notes": [
            "The inventory source does not contain a business snapshot date.",
            "Missing store-product combinations are not treated as zero stock.",
            "Explicit zero-stock records are different from absent inventory combinations."
        ],
    }


def main():
    """Run profiling and save the result as formatted JSON."""

    sources = load_sources()
    report = build_report(sources)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"Source profile written to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()