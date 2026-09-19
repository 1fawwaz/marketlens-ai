"""Shared tool handlers used by MCP servers and the investigation agent."""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, Field

from backend.app.ml.anomaly import get_anomalies
from backend.app.ml.forecast import get_forecast
from backend.app.ml.variance import get_monthly_summary, get_variance
from backend.app.query.safe_sql import QueryTemplate, SqlQuerySpec, execute_safe_query


class ForecastInput(BaseModel):
    category: str = Field(description="Product category")
    horizon_days: int = Field(description="Forecast horizon in days", ge=1, le=90)
    model_name: str = Field(default="xgboost")


class AnomalyInput(BaseModel):
    dimension_type: str = Field(description="state or category")
    start_date: str | None = None
    end_date: str | None = None


class VarianceInput(BaseModel):
    target_month: str = Field(description="First day of month YYYY-MM-DD")
    category: str | None = None


def handle_sql_query(spec: SqlQuerySpec) -> dict[str, Any]:
    return execute_safe_query(spec)


def handle_forecast(payload: ForecastInput) -> dict[str, Any]:
    rows = get_forecast(payload.category, payload.horizon_days, payload.model_name)
    total = sum(float(r["predicted_value"]) for r in rows)
    return {
        "category": payload.category,
        "horizon_days": payload.horizon_days,
        "model_name": payload.model_name,
        "forecast_total": round(total, 2),
        "points": rows,
        "is_experimental": payload.horizon_days == 90,
        "provenance": {
            "source": "forecast_results",
            "tool": "forecast",
            "query_id": f"FORECAST_{payload.category}_{payload.horizon_days}_{payload.model_name}",
        },
    }


def handle_anomaly_check(payload: AnomalyInput) -> dict[str, Any]:
    if payload.dimension_type not in {"state", "category"}:
        raise ValueError("dimension_type must be state or category")
    rows = get_anomalies(
        payload.dimension_type,
        start_date=payload.start_date,
        end_date=payload.end_date,
    )
    return {
        "dimension_type": payload.dimension_type,
        "anomaly_count": len(rows),
        "anomalies": rows,
        "provenance": {
            "source": "anomaly_flags",
            "tool": "anomaly_check",
            "query_id": f"ANOMALY_{payload.dimension_type}",
        },
        "note": "Anomalies indicate statistical outliers, not proven causal drivers.",
    }


def handle_variance(payload: VarianceInput) -> dict[str, Any]:
    if payload.category:
        rows = get_variance(target_month=payload.target_month, category=payload.category)
    else:
        summary = get_monthly_summary(payload.target_month)
        rows = summary.get("by_category", [])
    summary = get_monthly_summary(payload.target_month)
    return {
        "target_month": payload.target_month,
        "summary": summary,
        "rows": rows,
        "provenance": {
            "source": "variance_snapshots",
            "tool": "variance",
            "query_id": f"VARIANCE_{payload.target_month}",
        },
    }


def handle_rag_search(query: str, top_k: int = 5) -> dict[str, Any]:
    from backend.app.rag.search import hybrid_search

    results = hybrid_search(query, top_k=top_k)
    return {
        "query": query,
        "results": results,
        "provenance": {
            "source": "rag_documents",
            "tool": "rag_search",
            "query_id": f"RAG_{hash(query) & 0xFFFF:04x}",
        },
    }


def find_worst_variance_month() -> str | None:
    rows = get_variance()
    if not rows:
        return None
    agg: dict[str, float] = {}
    for row in rows:
        month = str(row["target_month"])
        agg[month] = agg.get(month, 0.0) + float(row["variance_amount"])
    if not agg:
        return None
    return min(agg, key=agg.get)
