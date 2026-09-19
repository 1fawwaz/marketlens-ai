"""Forecast evidence grain and Groq provider tests."""

from __future__ import annotations

import pytest
from sqlalchemy import text

from backend.app.agent.evidence import collect_evidence
from backend.app.agent.graph import run_investigation
from backend.app.config import get_settings, resolve_llm_backend
from backend.app.database import get_engine
from backend.app.llm.provider import get_llm_provider, probe_groq_api
from backend.app.ml.variance import get_monthly_summary


def _db_available() -> bool:
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _db_available(), reason="PostgreSQL unavailable")

FLAGSHIP = "We missed the sales target by 12%. What factors contributed to the gap?"


def test_forecast_evidence_uses_category_grain_not_company_total():
    result = run_investigation(FLAGSHIP)
    bundle = result["evidence_bundle"]
    fvt = bundle.get("forecast_vs_target")
    assert fvt is not None
    assert fvt["grain"] == "category"
    assert fvt["category"] == bundle["largest_miss_category"]

    summary = get_monthly_summary(result["target_month"])
    company_total_target = summary["total_target"]
    category_row = next(
        row for row in summary["by_category"] if row["category"] == fvt["category"]
    )
    category_target = round(float(category_row["target_amount"]), 2)

    assert fvt["target_total"] == category_target
    assert fvt["target_total"] != company_total_target
    assert fvt["delta"] == round(float(fvt["forecast_total"]) - category_target, 2)


def test_collect_evidence_rejects_mismatched_forecast_target_grains():
    summary = get_monthly_summary("2019-02-01")
    category = summary["largest_miss_category"]
    category_target = next(
        row["target_amount"] for row in summary["by_category"] if row["category"] == category
    )
    state = {
        "question": FLAGSHIP,
        "target_month": "2019-02-01",
        "tool_results": [
            {
                "tool": "variance",
                "payload": {"summary": summary, "provenance": {"query_id": "VARIANCE_2019-02-01"}},
            },
            {
                "tool": "forecast",
                "payload": {
                    "category": category,
                    "forecast_total": 8523.6,
                    "model_name": "xgboost",
                    "horizon_days": 30,
                    "is_experimental": False,
                    "provenance": {"query_id": f"FORECAST_{category}_30_xgboost"},
                },
            },
        ],
    }
    bundle = collect_evidence(state)
    fvt = bundle["forecast_vs_target"]
    assert fvt["grain"] == "category"
    assert fvt["target_total"] == round(float(category_target), 2)
    assert fvt["target_total"] != summary["total_target"]


def test_groq_selected_when_groq_key_present(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key-not-real")
    get_settings.cache_clear()
    assert resolve_llm_backend() == "groq"
    assert get_llm_provider().name == "groq"
    get_settings.cache_clear()


def test_deterministic_when_groq_key_missing(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "")
    get_settings.cache_clear()
    assert resolve_llm_backend() == "deterministic"
    assert get_llm_provider().name == "deterministic_fallback"
    get_settings.cache_clear()


@pytest.mark.groq_live
def test_groq_live_probe_when_key_configured(monkeypatch):
    from dotenv import dotenv_values

    from backend.app.config import ENV_FILE

    key = _clean_dotenv_secret(dotenv_values(ENV_FILE).get("GROQ_API_KEY"))
    if not key:
        pytest.skip("GROQ_API_KEY not configured in .env")
    monkeypatch.setenv("GROQ_API_KEY", key)
    get_settings.cache_clear()
    probe = probe_groq_api()
    assert probe["groq_configured"] is True
    if not probe["ok"]:
        pytest.fail(f"Groq probe failed: {probe.get('reason')}")


def _clean_dotenv_secret(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = str(value).strip()
    return stripped or None
