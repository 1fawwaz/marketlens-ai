"""Idempotent ETL: raw CSVs + festival reference -> PostgreSQL."""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
REFERENCE_DIR = PROJECT_ROOT / "data" / "reference"

if str(PROJECT_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
from db import get_engine  # noqa: E402


def parse_order_date(value: str) -> datetime:
    return datetime.strptime(value, "%d-%m-%Y")


def parse_target_month(value: str) -> datetime:
    """Convert MMM-YY (e.g. Apr-18) to first day of month."""
    return datetime.strptime(value, "%b-%y")


def load_orders() -> pd.DataFrame:
    df = pd.read_csv(RAW_DIR / "List of Orders.csv")
    df = df.dropna(subset=["Order ID"]).copy()
    df["order_id"] = df["Order ID"].astype(str).str.strip()
    df["order_date"] = df["Order Date"].apply(parse_order_date)
    df["customer_name"] = df["CustomerName"].astype(str).str.strip()
    df["customer_state"] = df["State"].astype(str).str.strip()
    df["customer_city"] = df["City"].astype(str).str.strip()
    return df[["order_id", "order_date", "customer_name", "customer_state", "customer_city"]]


def load_order_details() -> pd.DataFrame:
    df = pd.read_csv(RAW_DIR / "Order Details.csv")
    df["order_id"] = df["Order ID"].astype(str).str.strip()
    return df.rename(
        columns={
            "Category": "category",
            "Sub-Category": "sub_category",
            "Quantity": "quantity",
            "Amount": "amount",
            "Profit": "profit",
        }
    )[["order_id", "category", "sub_category", "quantity", "amount", "profit"]]


def load_sales_targets() -> pd.DataFrame:
    df = pd.read_csv(RAW_DIR / "Sales target.csv")
    df["target_month"] = df["Month of Order Date"].apply(parse_target_month)
    df["category"] = df["Category"].astype(str).str.strip()
    df["target_amount"] = df["Target"].astype(float)
    return df[["category", "target_month", "target_amount"]]


def load_festival_calendar() -> pd.DataFrame:
    df = pd.read_csv(REFERENCE_DIR / "festival_calendar.csv")
    df["festival_date"] = pd.to_datetime(df["festival_date"]).dt.date
    return df[["festival_date", "festival_name", "region_scope"]]


def truncate_tables(engine) -> None:
    """Clear transactional tables in FK-safe order."""
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE order_details RESTART IDENTITY CASCADE"))
        conn.execute(text("TRUNCATE TABLE orders RESTART IDENTITY CASCADE"))
        conn.execute(text("TRUNCATE TABLE sales_targets RESTART IDENTITY CASCADE"))
        conn.execute(text("TRUNCATE TABLE festival_calendar RESTART IDENTITY CASCADE"))


def run_etl(*, truncate: bool = True) -> dict:
    engine = get_engine()
    orders = load_orders()
    details = load_order_details()
    targets = load_sales_targets()
    festivals = load_festival_calendar()

    if truncate:
        truncate_tables(engine)

    orders.to_sql("orders", engine, if_exists="append", index=False, method="multi")
    details.to_sql("order_details", engine, if_exists="append", index=False, method="multi")
    targets.to_sql("sales_targets", engine, if_exists="append", index=False, method="multi")
    festivals.to_sql(
        "festival_calendar", engine, if_exists="append", index=False, method="multi"
    )

    row_counts = {
        "orders": len(orders),
        "order_details": len(details),
        "sales_targets": len(targets),
        "festival_calendar": len(festivals),
    }

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO etl_run_log (pipeline_name, finished_at, rows_loaded, status, message)
                VALUES (:name, NOW(), CAST(:rows AS jsonb), 'success', :message)
                """
            ),
            {
                "name": "raw_csv_to_postgres",
                "rows": json.dumps(row_counts),
                "message": "Idempotent reload completed",
            },
        )

    return row_counts


if __name__ == "__main__":
    counts = run_etl()
    print(json.dumps({"status": "success", "rows_loaded": counts}, indent=2))
