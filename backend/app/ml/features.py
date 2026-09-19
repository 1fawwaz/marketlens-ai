"""Build daily category sales from transactional tables."""

from __future__ import annotations

import pandas as pd
from sqlalchemy import text

from backend.app.database import get_engine


DAILY_SALES_SQL = """
SELECT
    o.order_date AS sales_date,
    d.category,
    SUM(d.amount) AS revenue,
    COUNT(DISTINCT o.order_id) AS order_count,
    SUM(d.quantity) AS quantity,
    SUM(d.profit) AS profit
FROM orders o
JOIN order_details d ON o.order_id = d.order_id
GROUP BY o.order_date, d.category
ORDER BY sales_date, category
"""


def compute_daily_category_sales() -> pd.DataFrame:
    engine = get_engine()
    return pd.read_sql(DAILY_SALES_SQL, engine, parse_dates=["sales_date"])


def persist_daily_category_sales(df: pd.DataFrame | None = None) -> int:
    engine = get_engine()
    if df is None:
        df = compute_daily_category_sales()
    payload = df.copy()
    payload["sales_date"] = pd.to_datetime(payload["sales_date"]).dt.date
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE daily_category_sales"))
        payload.to_sql(
            "daily_category_sales",
            conn,
            if_exists="append",
            index=False,
            method="multi",
        )
    return len(payload)
