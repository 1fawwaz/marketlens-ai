"""LangGraph investigation workflow."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from langgraph.graph import END, StateGraph

from backend.app.agent.evidence import InvestigationState, collect_evidence
from backend.app.investigation.month_resolver import MonthResolution, resolve_target_month
from backend.app.llm.provider import get_llm_provider
from backend.app.query.safe_sql import QueryTemplate, SqlQuerySpec
from backend.app.tools.handlers import (
    AnomalyInput,
    ForecastInput,
    VarianceInput,
    handle_anomaly_check,
    handle_forecast,
    handle_rag_search,
    handle_sql_query,
    handle_variance,
)


def _month_bounds(target_month: str) -> tuple[str, str]:
    dt = datetime.strptime(target_month, "%Y-%m-%d")
    if dt.month == 12:
        end = dt.replace(year=dt.year + 1, month=1, day=1)
    else:
        end = dt.replace(month=dt.month + 1, day=1)
    return target_month, (end - timedelta(days=1)).strftime("%Y-%m-%d")


def planner_node(state: InvestigationState) -> InvestigationState:
    question = state.get("question", "")
    resolution = resolve_target_month(
        question,
        context_month=state.get("context_month"),
    )
    provider = get_llm_provider()
    plan = provider.plan_investigation(
        question,
        {
            "target_month": resolution.target_month,
            "mode": resolution.mode,
            "requested_variance_pct": resolution.requested_variance_pct,
            "matched_variance_pct": resolution.matched_variance_pct,
        },
    )
    return {
        **state,
        "target_month": resolution.target_month,
        "month_resolution": {
            "mode": resolution.mode,
            "requested_variance_pct": resolution.requested_variance_pct,
            "matched_variance_pct": resolution.matched_variance_pct,
        },
        "planned_tools": plan.get("tools", []),
        "planner_provider": plan.get("provider"),
        "planner_rationale": plan.get("rationale"),
        "tool_results": [],
    }


def tool_executor_node(state: InvestigationState) -> InvestigationState:
    target_month = state.get("target_month")
    if not target_month:
        raise ValueError("target_month missing from planner state")
    month_start, month_end = _month_bounds(target_month)
    planned = set(state.get("planned_tools") or [])
    results: list[dict[str, Any]] = []

    if "variance" in planned or not planned:
        variance_payload = handle_variance(VarianceInput(target_month=target_month))
        results.append({"tool": "variance", "payload": variance_payload})

    if "sql_query:revenue_by_state" in planned or not planned:
        region_payload = handle_sql_query(
            SqlQuerySpec(
                template=QueryTemplate.REVENUE_BY_STATE,
                start_date=month_start,
                end_date=month_end,
            )
        )
        results.append(
            {
                "tool": "sql_query",
                "template": "revenue_by_state",
                "payload": region_payload,
            }
        )

    if "sql_query:festivals_in_range" in planned or not planned:
        festival_payload = handle_sql_query(
            SqlQuerySpec(
                template=QueryTemplate.FESTIVALS_IN_RANGE,
                start_date=month_start,
                end_date=month_end,
            )
        )
        results.append(
            {
                "tool": "sql_query",
                "template": "festivals_in_range",
                "payload": festival_payload,
            }
        )

    worst_cat = "Clothing"
    for item in results:
        if item.get("tool") == "variance":
            worst_cat = item["payload"].get("summary", {}).get("largest_miss_category", worst_cat)
            break

    if "forecast" in planned or not planned:
        forecast_payload = handle_forecast(
            ForecastInput(category=worst_cat, horizon_days=30, model_name="xgboost")
        )
        results.append({"tool": "forecast", "payload": forecast_payload})

    if "anomaly_check" in planned or not planned:
        anomaly_payload = handle_anomaly_check(
            AnomalyInput(dimension_type="state", start_date=month_start, end_date=month_end)
        )
        results.append({"tool": "anomaly_check", "payload": anomaly_payload})

    if "rag_search" in planned:
        rag_payload = handle_rag_search("target miss escalation process", top_k=3)
        results.append({"tool": "rag_search", "payload": rag_payload})

    return {**state, "tool_results": results}


def evidence_node(state: InvestigationState) -> InvestigationState:
    bundle = collect_evidence(state)
    bundle["month_resolution"] = state.get("month_resolution")
    bundle["planner_provider"] = state.get("planner_provider")
    return {**state, "evidence_bundle": bundle}


def report_node(state: InvestigationState) -> InvestigationState:
    bundle = state.get("evidence_bundle", {})
    provider = get_llm_provider()
    report = provider.generate_report(bundle)
    report_provider = provider.name
    return {**state, "final_report": report, "report_provider": report_provider}


def build_investigation_graph():
    graph = StateGraph(InvestigationState)
    graph.add_node("planner", planner_node)
    graph.add_node("tools", tool_executor_node)
    graph.add_node("evidence", evidence_node)
    graph.add_node("report", report_node)
    graph.set_entry_point("planner")
    graph.add_edge("planner", "tools")
    graph.add_edge("tools", "evidence")
    graph.add_edge("evidence", "report")
    graph.add_edge("report", END)
    return graph.compile()


def run_investigation(
    question: str,
    context_month: str | None = None,
) -> dict[str, Any]:
    app = build_investigation_graph()
    result = app.invoke({"question": question, "context_month": context_month})
    return {
        "question": question,
        "target_month": result.get("target_month"),
        "month_resolution": result.get("month_resolution"),
        "planner_provider": result.get("planner_provider"),
        "report_provider": result.get("report_provider"),
        "evidence_bundle": result.get("evidence_bundle"),
        "report": result.get("final_report"),
        "tool_results": result.get("tool_results"),
    }
