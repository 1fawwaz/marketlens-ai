"""Basic forecast drift monitoring."""

from __future__ import annotations

from sqlalchemy import text

from backend.app.database import get_engine


def run_drift_check(degradation_threshold: float = 1.25) -> list[dict]:
    engine = get_engine()
    query = text(
        """
        SELECT category, model_name, horizon_days, mae
        FROM forecast_evaluations
        WHERE model_name = 'xgboost'
        ORDER BY category, horizon_days
        """
    )
    baseline_query = text(
        """
        SELECT category, model_name, horizon_days, mae
        FROM forecast_evaluations
        WHERE model_name = 'naive_baseline'
        """
    )
    with engine.connect() as conn:
        model_rows = conn.execute(query).mappings().all()
        baseline_rows = {
            (r["category"], r["horizon_days"]): float(r["mae"])
            for r in conn.execute(baseline_query).mappings().all()
        }

    logs = []
    with engine.begin() as conn:
        for row in model_rows:
            key = (row["category"], row["horizon_days"])
            baseline_mae = baseline_rows.get(key, 0.0) or 0.001
            mae = float(row["mae"])
            ratio = mae / baseline_mae
            is_degraded = ratio > degradation_threshold
            conn.execute(
                text(
                    """
                    INSERT INTO forecast_drift_log
                    (category, model_name, horizon_days, window_start, window_end,
                     mae, baseline_mae, drift_ratio, is_degraded)
                    VALUES (:category, :model_name, :horizon_days,
                            DATE '2018-04-01', DATE '2019-03-31',
                            :mae, :baseline_mae, :drift_ratio, :is_degraded)
                    """
                ),
                {
                    "category": row["category"],
                    "model_name": row["model_name"],
                    "horizon_days": row["horizon_days"],
                    "mae": mae,
                    "baseline_mae": baseline_mae,
                    "drift_ratio": round(ratio, 4),
                    "is_degraded": is_degraded,
                },
            )
            logs.append(
                {
                    "category": row["category"],
                    "horizon_days": row["horizon_days"],
                    "mae": mae,
                    "baseline_mae": baseline_mae,
                    "drift_ratio": round(ratio, 4),
                    "is_degraded": is_degraded,
                }
            )
    return logs
