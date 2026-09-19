"""Orchestrate Phase 1 ML pipeline."""

from __future__ import annotations

from backend.app.ml.anomaly import run_anomaly_detection
from backend.app.ml.features import persist_daily_category_sales
from backend.app.ml.forecast import run_forecasting_pipeline
from backend.app.ml.variance import persist_variance_snapshots


def run_ml_pipeline() -> dict:
    daily_rows = persist_daily_category_sales()
    variance_rows = persist_variance_snapshots()
    forecast_stats = run_forecasting_pipeline()
    anomaly_stats = run_anomaly_detection(validate_injection=True)
    return {
        "daily_category_sales": daily_rows,
        "variance_snapshots": variance_rows,
        **forecast_stats,
        **anomaly_stats,
    }


if __name__ == "__main__":
    import json

    print(json.dumps(run_ml_pipeline(), indent=2, default=str))
