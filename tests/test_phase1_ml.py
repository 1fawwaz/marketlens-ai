"""Phase 1 ML tests."""

from __future__ import annotations

import pytest
from sqlalchemy import text

from backend.app.database import get_engine
from backend.app.ml.anomaly import run_anomaly_detection
from backend.app.ml.features import persist_daily_category_sales
from backend.app.ml.forecast import run_forecasting_pipeline
from backend.app.ml.pipeline import run_ml_pipeline
from backend.app.ml.variance import compute_variance_snapshots, persist_variance_snapshots


def _db_available() -> bool:
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _db_available(), reason="PostgreSQL unavailable")


@pytest.fixture(scope="module")
def ml_ready():
    persist_daily_category_sales()
    persist_variance_snapshots()
    run_forecasting_pipeline()
    run_anomaly_detection(validate_injection=True)


def test_daily_sales_rows(ml_ready):
    with get_engine().connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM daily_category_sales")).scalar()
    assert count > 0


def test_variance_snapshots_joinable(ml_ready):
    df = compute_variance_snapshots()
    assert len(df) == 36
    assert df["variance_amount"].notna().all()


def test_forecast_evaluations_exist(ml_ready):
    with get_engine().connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM forecast_evaluations")).scalar()
    assert count == 27  # 3 categories x 3 models x 3 horizons


def test_naive_baseline_recorded(ml_ready):
    with get_engine().connect() as conn:
        count = conn.execute(
            text("SELECT COUNT(*) FROM forecast_evaluations WHERE model_name='naive_baseline'")
        ).scalar()
    assert count == 9


def test_90_day_marked_experimental(ml_ready):
    with get_engine().connect() as conn:
        row = conn.execute(
            text(
                "SELECT is_experimental FROM forecast_results WHERE horizon_days=90 LIMIT 1"
            )
        ).fetchone()
    assert row[0] is True


def test_anomaly_injection_validation(ml_ready):
    stats = run_anomaly_detection(validate_injection=True)
    assert stats["detector"] == "isolation_forest"
    assert stats["injection_total"] > 0
    assert stats["injection_hits"] >= 1


def test_ml_pipeline_idempotent():
    first = run_ml_pipeline()
    second = run_ml_pipeline()
    assert first["forecasts"] == second["forecasts"]
