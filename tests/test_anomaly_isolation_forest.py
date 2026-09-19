"""Isolation Forest verification tests."""

from __future__ import annotations

import pytest
from sqlalchemy import text

from backend.app.database import get_engine
from backend.app.ml.anomaly import inject_known_anomalies, run_anomaly_detection
from backend.app.ml.sklearn_runtime import isolation_forest_available, require_isolation_forest


def _db_available() -> bool:
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _db_available(), reason="PostgreSQL unavailable")


def test_isolation_forest_runtime_available():
    assert isolation_forest_available(probe=True) is True
    require_isolation_forest()


def test_injected_anomaly_validation_uses_isolation_forest():
    stats = run_anomaly_detection(validate_injection=True)
    assert stats["detector"] == "isolation_forest"
    assert stats["injection_total"] > 0
    assert stats["injection_hits"] >= 1


def test_no_zscore_substitution_by_default(monkeypatch):
    monkeypatch.delenv("ANOMALY_DETECTOR_FALLBACK", raising=False)
    stats = run_anomaly_detection(validate_injection=True)
    assert stats["detector"] == "isolation_forest"


def test_explicit_zscore_fallback_is_labeled(monkeypatch):
    import backend.app.ml.sklearn_runtime as runtime

    monkeypatch.setenv("ANOMALY_DETECTOR_FALLBACK", "zscore")
    monkeypatch.setattr(runtime, "_ISOLATION_FOREST_OK", False)
    monkeypatch.setattr(runtime, "_ISOLATION_FOREST_ERROR", "forced for test")
    stats = run_anomaly_detection(validate_injection=False)
    assert stats["detector"] == "zscore_fallback"
