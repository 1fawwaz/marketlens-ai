"""Phase 2 MCP handler/schema tests."""

from __future__ import annotations

import pytest

from backend.app.query.safe_sql import QueryTemplate, SqlQuerySpec, execute_safe_query
from backend.app.tools.handlers import (
    AnomalyInput,
    ForecastInput,
    VarianceInput,
    handle_anomaly_check,
    handle_forecast,
    handle_rag_search,
    handle_variance,
)


def test_sql_query_rejects_invalid_category():
    with pytest.raises(ValueError):
        SqlQuerySpec(template=QueryTemplate.REVENUE_BY_STATE, category="Invalid")


def test_sql_query_returns_provenance():
    result = execute_safe_query(
        SqlQuerySpec(template=QueryTemplate.FESTIVALS_IN_RANGE, start_date="2018-11-01", end_date="2018-11-30")
    )
    assert result["provenance"]["method"] == "parameterized_template"
    assert result["row_count"] >= 1


def test_forecast_handler():
    result = handle_forecast(ForecastInput(category="Clothing", horizon_days=7))
    assert "forecast_total" in result
    assert result["provenance"]["tool"] == "forecast"


def test_variance_handler():
    result = handle_variance(VarianceInput(target_month="2018-11-01"))
    assert "summary" in result
    assert result["provenance"]["tool"] == "variance"


def test_anomaly_handler():
    result = handle_anomaly_check(AnomalyInput(dimension_type="category"))
    assert "anomalies" in result
    assert "not proven causal" in result["note"]


def test_rag_handler():
    result = handle_rag_search("target miss escalation")
    assert "results" in result
    if result["results"]:
        assert result["results"][0]["is_synthetic"] is True
        assert "citation" in result["results"][0]


@pytest.mark.parametrize(
    "module_path,tool_name",
    [
        ("mcp_servers.sql_query.server", "sql_query"),
        ("mcp_servers.forecast.server", "forecast"),
        ("mcp_servers.anomaly_check.server", "anomaly_check"),
        ("mcp_servers.variance.server", "variance"),
        ("mcp_servers.rag_search.server", "rag_search"),
    ],
)
def test_mcp_server_modules_import(module_path, tool_name):
    import importlib

    mod = importlib.import_module(module_path)
    assert mod.mcp is not None
