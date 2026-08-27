"""Create reproducible monthly sales load files.

Run from the repository root:

    python scripts/create_sales_batches.py
"""

from pathlib import Path

import pandas as pd


SOURCE_FILE = Path("data/raw/maven_toys/sales.csv")
OUTPUT_DIR = Path("data/raw/maven_toys/load_batches")


def load_sales():
    """Load the original sales file and parse its transaction date."""

    sales_df = pd.read_csv(
        SOURCE_FILE,
        dtype={
            "Sale_ID": "string",
            "Store_ID": "string",
            "Product_ID": "string",
            "Units": "Int64",
        },
        parse_dates=["Date"],
    )

    return sales_df


def create_monthly_batches(sales_df):
    """Write one sales file for each calendar month."""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    batch_counts = {}

    monthly_groups = sales_df.groupby(
        sales_df["Date"].dt.to_period("M"),
        sort=True,
    )

    for month, batch_df in monthly_groups:
        file_name = f"sales_{month.strftime('%Y_%m')}.csv"
        output_file = OUTPUT_DIR / file_name

        batch_df.to_csv(
            output_file,
            index=False,
            date_format="%Y-%m-%d",
        )

        batch_counts[file_name] = len(batch_df)

    return batch_counts


def main():
    """Generate monthly sales files and print a summary."""

    sales_df = load_sales()
    batch_counts = create_monthly_batches(sales_df)

    for file_name, row_count in batch_counts.items():
        print(f"{file_name}: {row_count:,} rows")

    print(f"Files created: {len(batch_counts)}")
    print(f"Total rows: {sum(batch_counts.values()):,}")


if __name__ == "__main__":
    main()