"""Phase 3 investigation agent tests."""

from __future__ import annotations

import pytest
from sqlalchemy import text

from backend.app.agent.graph import run_investigation
from backend.app.database import get_engine


def _db_available() -> bool:
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _db_available(), reason="PostgreSQL unavailable")


FLAGSHIP = "We missed the sales target by 12%. What factors contributed to the gap?"


def test_flagship_uses_percent_match_not_worst_month():
    result = run_investigation(FLAGSHIP)
    assert result["month_resolution"]["mode"] == "percent_match"
    assert result["target_month"] == "2019-02-01"
    assert result["target_month"] != "2018-07-01"


def test_flagship_investigation_structure():
    result = run_investigation(FLAGSHIP)
    bundle = result["evidence_bundle"]
    assert bundle["target"] is not None
    assert bundle["actual"] is not None
    assert bundle["variance_pct"] is not None
    assert bundle["largest_miss_category"]
    assert bundle["supporting_query_ids"]


def test_report_cites_evidence_ids():
    result = run_investigation(FLAGSHIP)
    report = result["report"]
    bundle = result["evidence_bundle"]
    assert "VARIANCE_2019-02-01" in report or "VARIANCE_2019-02-01" in bundle["supporting_query_ids"]
    assert bundle["supporting_query_ids"]


def test_report_provider_declared():
    result = run_investigation(FLAGSHIP)
    assert result["report_provider"] in {"deterministic_fallback", "groq"}


def test_flagship_forecast_section_uses_category_grain():
    result = run_investigation(FLAGSHIP)
    fvt = result["evidence_bundle"].get("forecast_vs_target")
    assert fvt is not None
    assert fvt["grain"] == "category"
    assert fvt["target_total"] != result["evidence_bundle"]["target"]
