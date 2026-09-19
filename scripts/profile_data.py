"""Phase 0 data profiling script — reads raw CSVs and prints JSON profile."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"


def profile_df(name: str, df: pd.DataFrame) -> dict:
    return {
        "file": name,
        "row_count": len(df),
        "columns": list(df.columns),
        "dtypes": {c: str(df[c].dtype) for c in df.columns},
        "null_counts": df.isnull().sum().to_dict(),
        "duplicate_rows": int(df.duplicated().sum()),
    }


def main() -> None:
    orders = pd.read_csv(RAW_DIR / "List of Orders.csv")
    details = pd.read_csv(RAW_DIR / "Order Details.csv")
    targets = pd.read_csv(RAW_DIR / "Sales target.csv")

    profiles: dict = {}
    profiles["List of Orders.csv"] = profile_df("List of Orders.csv", orders)
    profiles["Order Details.csv"] = profile_df("Order Details.csv", details)
    profiles["Sales target.csv"] = profile_df("Sales target.csv", targets)

    orders["order_date_parsed"] = pd.to_datetime(
        orders["Order Date"], format="%d-%m-%Y", errors="coerce"
    )
    o = profiles["List of Orders.csv"]
    o["unique_order_ids"] = int(orders["Order ID"].nunique())
    o["duplicate_order_ids"] = int(orders["Order ID"].duplicated().sum())
    o["date_min"] = str(orders["order_date_parsed"].min())
    o["date_max"] = str(orders["order_date_parsed"].max())
    o["invalid_dates"] = int(orders["order_date_parsed"].isna().sum())
    o["unique_states"] = int(orders["State"].nunique())
    o["unique_cities"] = int(orders["City"].nunique())
    o["unique_customers"] = int(orders["CustomerName"].nunique())
    o["states"] = sorted(
        [s for s in orders["State"].dropna().unique().tolist() if isinstance(s, str)]
    )

    d = profiles["Order Details.csv"]
    d["unique_order_ids"] = int(details["Order ID"].nunique())
    d["unique_categories"] = sorted(details["Category"].unique().tolist())
    d["unique_subcategories"] = int(details["Sub-Category"].nunique())
    d["subcategories"] = sorted(details["Sub-Category"].unique().tolist())
    sizes = details.groupby("Order ID").size()
    d["line_items_per_order"] = {
        "min": int(sizes.min()),
        "max": int(sizes.max()),
        "mean": round(float(sizes.mean()), 2),
    }
    d["amount_stats"] = {
        "min": float(details["Amount"].min()),
        "max": float(details["Amount"].max()),
        "sum": float(details["Amount"].sum()),
    }

    t = profiles["Sales target.csv"]
    t["unique_categories"] = sorted(targets["Category"].unique().tolist())
    t["unique_months"] = sorted(targets["Month of Order Date"].unique().tolist())
    t["month_count"] = int(targets["Month of Order Date"].nunique())
    t["duplicate_category_month"] = int(
        targets.duplicated(subset=["Month of Order Date", "Category"]).sum()
    )
    t["grain"] = "one row per (Month of Order Date, Category)"
    t["month_format"] = "MMM-YY e.g. Apr-18"

    order_ids_orders = set(orders["Order ID"])
    order_ids_details = set(details["Order ID"])
    profiles["join_integrity"] = {
        "orders_in_details_not_in_orders": sorted(order_ids_details - order_ids_orders),
        "orders_in_orders_not_in_details": sorted(order_ids_orders - order_ids_details),
        "count_orphan_details": len(order_ids_details - order_ids_orders),
        "count_orders_without_details": len(order_ids_orders - order_ids_details),
        "categories_in_details": sorted(details["Category"].unique().tolist()),
        "categories_in_targets": sorted(targets["Category"].unique().tolist()),
        "categories_in_details_not_in_targets": sorted(
            set(details["Category"]) - set(targets["Category"])
        ),
        "categories_in_targets_not_in_details": sorted(
            set(targets["Category"]) - set(details["Category"])
        ),
        "join_key_orders_to_details": "Order ID",
        "join_key_details_to_targets": "Category + month derived from Order Date",
    }

    profiles["data_quality"] = {
        "states_with_trailing_space": [
            s
            for s in orders["State"].dropna().unique()
            if isinstance(s, str) and s != s.strip()
        ],
        "cities_with_trailing_space": [
            c
            for c in orders["City"].dropna().unique()
            if isinstance(c, str) and c != c.strip()
        ],
        "null_state_count": int(orders["State"].isna().sum()),
        "null_city_count": int(orders["City"].isna().sum()),
        "null_customer_name_count": int(orders["CustomerName"].isna().sum()),
        "customer_names_present": True,
        "privacy_note": "Real customer names in source; minimize exposure in UI",
    }

    profiles["spec_discrepancies"] = [
        {
            "field": "orders.customer_name",
            "spec": "customer_name",
            "actual": "CustomerName",
        },
        {
            "field": "orders.customer_state",
            "spec": "customer_state",
            "actual": "State",
        },
        {
            "field": "orders.customer_city",
            "spec": "customer_city",
            "actual": "City",
        },
        {
            "field": "order_details.price",
            "spec": "price",
            "actual": "Amount",
        },
        {
            "field": "sales_targets.target_amount",
            "spec": "target_amount",
            "actual": "Target",
        },
        {
            "field": "sales_targets.month",
            "spec": "month",
            "actual": "Month of Order Date (MMM-YY string, not date)",
        },
        {
            "field": "order grain",
            "spec": "one row per order",
            "actual": "560 orders, 560 rows — one row per order (1:1)",
        },
        {
            "field": "order_details grain",
            "spec": "line items per order",
            "actual": f"{len(details)} line items across {details['Order ID'].nunique()} orders",
        },
    ]

    print(json.dumps(profiles, indent=2, default=str))


if __name__ == "__main__":
    main()
