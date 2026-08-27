# Source data

## Dataset

Mexico Toy Sales from the Maven Analytics Data Playground:

https://mavenanalytics.io/data-playground/mexico-toy-sales

The dataset represents a fictional toy-store chain in Mexico and includes daily sales transactions, products, stores, a calendar, and current inventory by store and product.

The source page identifies the dataset as Public Domain.

## Expected files

```text
calendar.csv
data_dictionary.csv
inventory.csv
products.csv
sales.csv
stores.csv
```

## Local placement

Download and extract the original files into:

```text
data/raw/maven_toys/
```

The `data/raw/` directory is excluded from Git because the complete source data can be downloaded separately.

Do not modify the original source files. Cleaning and transformation will take place in Fabric Bronze, Silver, and Gold layers.

## Source limitations

The inventory file contains current stock on hand for each store-product combination. It does not provide:

- historical snapshot dates
- replenishment events
- stock movements
- purchase orders
- supplier lead times
- recorded lost sales

Any inventory-risk metrics must be interpreted using these limitations.