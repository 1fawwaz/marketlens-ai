"""LLM provider tests."""

from __future__ import annotations

from backend.app.llm.provider import DeterministicLLMProvider, get_llm_provider, llm_status


def test_default_provider_is_deterministic_without_api_keys(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "")
    from backend.app.config import get_settings

    get_settings.cache_clear()
    provider = get_llm_provider()
    assert provider.name == "deterministic_fallback"


def test_deterministic_report_uses_evidence_only():
    provider = DeterministicLLMProvider()
    evidence = {
        "question": "test",
        "target_month": "2019-02-01",
        "target": 100.0,
        "actual": 87.0,
        "variance_amount": -13.0,
        "variance_pct": -13.0,
        "largest_miss_category": "Clothing",
        "largest_miss_variance_pct": -5.0,
        "largest_contributing_region": "Maharashtra",
        "supporting_query_ids": ["VARIANCE_2019-02-01"],
        "notes": [],
    }
    report = provider.generate_report(evidence)
    assert "₹100.0" in report
    assert "VARIANCE_2019-02-01" in report
    assert "deterministic_fallback" in report


def test_llm_status_reports_fallback():
    status = llm_status()
    assert "active_provider" in status
    assert "using_fallback" in status
