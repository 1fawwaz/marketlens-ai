"""Target Achievement Engine — actual vs target variance analysis."""

from __future__ import annotations

from datetime import date

import pandas as pd
from sqlalchemy import text

from backend.app.database import get_engine

ACTUAL_BY_MONTH_SQL = """
SELECT DATE_TRUNC('month', o.order_date)::date AS target_month,
       d.category,
       SUM(d.amount) AS actual_amount
FROM orders o
JOIN order_details d ON o.order_id = d.order_id
GROUP BY 1, 2
"""

TOP_STATE_SQL = """
SELECT DATE_TRUNC('month', o.order_date)::date AS target_month,
       d.category,
       o.customer_state AS customer_state,
       SUM(d.amount) AS state_amount
FROM orders o
JOIN order_details d ON o.order_id = d.order_id
WHERE DATE_TRUNC('month', o.order_date)::date = :target_month
  AND d.category = :category
GROUP BY 1, 2, 3
ORDER BY state_amount DESC
LIMIT 1
"""


def compute_variance_snapshots() -> pd.DataFrame:
    engine = get_engine()
    actual = pd.read_sql(ACTUAL_BY_MONTH_SQL, engine)
    targets = pd.read_sql(
        "SELECT category, target_month, target_amount FROM sales_targets",
        engine,
    )
    merged = actual.merge(targets, on=["target_month", "category"], how="inner")
    merged["variance_amount"] = merged["actual_amount"] - merged["target_amount"]
    merged["variance_pct"] = (
        merged["variance_amount"] / merged["target_amount"].replace(0, pd.NA) * 100
    ).round(4)

    top_states = []
    with engine.connect() as conn:
        for _, row in merged.iterrows():
            top = conn.execute(
                text(TOP_STATE_SQL),
                {
                    "target_month": row["target_month"],
                    "category": row["category"],
                },
            ).mappings().first()
            top_states.append(
                {
                    "top_state": top["customer_state"] if top else None,
                    "top_state_amount": float(top["state_amount"]) if top else None,
                }
            )
    merged["top_state"] = [t["top_state"] for t in top_states]
    merged["top_state_amount"] = [t["top_state_amount"] for t in top_states]
    return merged


def persist_variance_snapshots(df: pd.DataFrame | None = None) -> int:
    engine = get_engine()
    if df is None:
        df = compute_variance_snapshots()
    payload = df[
        [
            "target_month",
            "category",
            "target_amount",
            "actual_amount",
            "variance_amount",
            "variance_pct",
            "top_state",
            "top_state_amount",
        ]
    ].copy()
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE variance_snapshots RESTART IDENTITY"))
        payload.to_sql("variance_snapshots", conn, if_exists="append", index=False, method="multi")
    return len(payload)


def get_variance(
    target_month: date | str | None = None,
    category: str | None = None,
) -> list[dict]:
    engine = get_engine()
    clauses = []
    params: dict = {}
    if target_month:
        clauses.append("target_month = :target_month")
        params["target_month"] = target_month
    if category:
        clauses.append("category = :category")
        params["category"] = category
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    query = text(
        f"""
        SELECT snapshot_id, target_month, category, target_amount, actual_amount,
               variance_amount, variance_pct, top_state, top_state_amount
        FROM variance_snapshots
        {where}
        ORDER BY target_month, category
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(query, params).mappings().all()
    return [dict(r) for r in rows]


def get_monthly_summary(target_month: date | str) -> dict:
    rows = get_variance(target_month=target_month)
    if not rows:
        return {}
    total_target = sum(float(r["target_amount"]) for r in rows)
    total_actual = sum(float(r["actual_amount"]) for r in rows)
    variance = total_actual - total_target
    variance_pct = (variance / total_target * 100) if total_target else 0.0
    worst = min(rows, key=lambda r: float(r["variance_pct"]))
    best_state = max(rows, key=lambda r: float(r["top_state_amount"] or 0))
    return {
        "target_month": str(target_month),
        "total_target": round(total_target, 2),
        "total_actual": round(total_actual, 2),
        "variance_amount": round(variance, 2),
        "variance_pct": round(variance_pct, 2),
        "largest_miss_category": worst["category"],
        "largest_miss_variance_pct": float(worst["variance_pct"]),
        "largest_state": best_state["top_state"],
        "by_category": rows,
    }
