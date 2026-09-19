"""Isolation Forest anomaly detection with injected validation support."""

from __future__ import annotations

import os

import pandas as pd
from sqlalchemy import text

from backend.app.database import get_engine
from backend.app.ml.sklearn_runtime import (
    active_detector_name,
    isolation_forest_available,
    require_isolation_forest,
)

STATE_DAILY_SQL = """
SELECT o.order_date AS anomaly_date,
       o.customer_state AS dimension_value,
       SUM(d.amount) AS metric_value
FROM orders o
JOIN order_details d ON o.order_id = d.order_id
GROUP BY o.order_date, o.customer_state
"""

CATEGORY_DAILY_SQL = """
SELECT o.order_date AS anomaly_date,
       d.category AS dimension_value,
       SUM(d.amount) AS metric_value
FROM orders o
JOIN order_details d ON o.order_id = d.order_id
GROUP BY o.order_date, d.category
"""


def _zscore_fallback_detect(
    df: pd.DataFrame, dimension_type: str, threshold: float = 2.5
) -> pd.DataFrame:
    """Explicit fallback only — not equivalent to Isolation Forest."""
    records = []
    for dim_value, grp in df.groupby("dimension_value"):
        grp = grp.sort_values("anomaly_date").copy()
        if len(grp) < 10:
            continue
        values = grp["metric_value"].astype(float)
        mean = values.mean()
        std = values.std() or 1.0
        zscores = (values - mean) / std
        for idx, row in grp.iterrows():
            pos = grp.index.get_loc(idx)
            z = float(zscores.iloc[pos])
            records.append(
                {
                    "dimension_type": dimension_type,
                    "dimension_value": dim_value,
                    "anomaly_date": pd.to_datetime(row["anomaly_date"]).date(),
                    "metric_name": "revenue",
                    "metric_value": float(row["metric_value"]),
                    "anomaly_score": z,
                    "is_anomaly": abs(z) >= threshold,
                    "is_injected": False,
                }
            )
    return pd.DataFrame(records)


def _isolation_forest_detect(
    df: pd.DataFrame, dimension_type: str, contamination: float = 0.05
) -> pd.DataFrame:
    from sklearn.ensemble import IsolationForest

    records = []
    for dim_value, grp in df.groupby("dimension_value"):
        grp = grp.sort_values("anomaly_date").copy()
        if len(grp) < 10:
            continue
        values = grp["metric_value"].astype(float).values.reshape(-1, 1)
        model = IsolationForest(
            contamination=contamination,
            random_state=42,
            n_estimators=100,
        )
        scores = model.fit_predict(values)
        anomaly_scores = model.decision_function(values)
        for idx, row in grp.iterrows():
            pos = grp.index.get_loc(idx)
            records.append(
                {
                    "dimension_type": dimension_type,
                    "dimension_value": dim_value,
                    "anomaly_date": pd.to_datetime(row["anomaly_date"]).date(),
                    "metric_name": "revenue",
                    "metric_value": float(row["metric_value"]),
                    "anomaly_score": float(anomaly_scores[pos]),
                    "is_anomaly": bool(scores[pos] == -1),
                    "is_injected": False,
                }
            )
    return pd.DataFrame(records)


def _detect(df: pd.DataFrame, dimension_type: str, contamination: float = 0.05) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    if isolation_forest_available():
        return _isolation_forest_detect(df, dimension_type, contamination)
    if os.getenv("ANOMALY_DETECTOR_FALLBACK", "").lower() == "zscore":
        return _zscore_fallback_detect(df, dimension_type)
    require_isolation_forest()
    return pd.DataFrame()


def inject_known_anomalies(
    df: pd.DataFrame, multiplier: float = 5.0
) -> tuple[pd.DataFrame, set[tuple]]:
    injected_keys: set[tuple] = set()
    test = df.copy()
    for dim_value, grp in test.groupby("dimension_value"):
        grp = grp.sort_values("anomaly_date")
        if len(grp) < 15:
            continue
        target_idx = grp.index[-3]
        original = float(test.loc[target_idx, "metric_value"])
        test.loc[target_idx, "metric_value"] = original * multiplier
        injected_keys.add(
            (
                dim_value,
                pd.to_datetime(test.loc[target_idx, "anomaly_date"]).date(),
            )
        )
    return test, injected_keys


def run_anomaly_detection(*, validate_injection: bool = True) -> dict:
    require_isolation_forest()
    engine = get_engine()
    state_df = pd.read_sql(STATE_DAILY_SQL, engine, parse_dates=["anomaly_date"])
    category_df = pd.read_sql(CATEGORY_DAILY_SQL, engine, parse_dates=["anomaly_date"])

    injection_hits = 0
    injection_total = 0
    if validate_injection and not state_df.empty:
        injected_df, injected_keys = inject_known_anomalies(state_df)
        injection_total = len(injected_keys)
        detected = _detect(injected_df, "state")
        for key in injected_keys:
            dim, dt = key
            hit = detected[
                (detected["dimension_value"] == dim)
                & (detected["anomaly_date"] == dt)
                & (detected["is_anomaly"])
            ]
            if not hit.empty:
                injection_hits += 1
                detected.loc[hit.index, "is_injected"] = True
        state_flags = detected
    else:
        state_flags = _detect(state_df, "state")

    category_flags = _detect(category_df, "category")
    all_flags = pd.concat([state_flags, category_flags], ignore_index=True)

    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE anomaly_flags RESTART IDENTITY"))
        if not all_flags.empty:
            all_flags.to_sql("anomaly_flags", conn, if_exists="append", index=False, method="multi")

    return {
        "detector": active_detector_name(),
        "flags": len(all_flags),
        "anomalies": int(all_flags["is_anomaly"].sum()) if not all_flags.empty else 0,
        "injection_total": injection_total,
        "injection_hits": injection_hits,
    }


def get_anomalies(
    dimension_type: str,
    start_date: str | None = None,
    end_date: str | None = None,
    only_anomalies: bool = True,
) -> list[dict]:
    engine = get_engine()
    clauses = ["dimension_type = :dimension_type"]
    params: dict = {"dimension_type": dimension_type}
    if only_anomalies:
        clauses.append("is_anomaly = TRUE")
    if start_date:
        clauses.append("anomaly_date >= :start_date")
        params["start_date"] = start_date
    if end_date:
        clauses.append("anomaly_date <= :end_date")
        params["end_date"] = end_date
    query = text(
        f"""
        SELECT anomaly_id, dimension_type, dimension_value, anomaly_date,
               metric_name, metric_value, anomaly_score, is_anomaly, is_injected
        FROM anomaly_flags
        WHERE {' AND '.join(clauses)}
        ORDER BY anomaly_date DESC
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(query, params).mappings().all()
    return [dict(r) for r in rows]
