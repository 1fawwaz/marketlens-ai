"""Investigation state and evidence collection."""

from __future__ import annotations

from typing import Any, TypedDict


class InvestigationState(TypedDict, total=False):
    question: str
    context_month: str | None
    target_month: str | None
    month_resolution: dict[str, Any]
    planned_tools: list[str]
    planner_provider: str | None
    planner_rationale: str | None
    tool_results: list[dict[str, Any]]
    evidence_bundle: dict[str, Any]
    final_report: str
    report_provider: str | None


def collect_evidence(state: InvestigationState) -> dict[str, Any]:
    results = state.get("tool_results", [])
    variance = next((r for r in results if r.get("tool") == "variance"), None)
    forecast = next((r for r in results if r.get("tool") == "forecast"), None)
    anomaly = next((r for r in results if r.get("tool") == "anomaly_check"), None)
    sql_results = [r for r in results if r.get("tool") == "sql_query"]
    festival = next(
        (r for r in sql_results if r.get("template") == "festivals_in_range"),
        None,
    )
    region = next(
        (r for r in sql_results if r.get("template") == "revenue_by_state"),
        None,
    )

    summary = (variance or {}).get("payload", {}).get("summary", {})
    bundle = {
        "question": state.get("question"),
        "target_month": state.get("target_month"),
        "target": summary.get("total_target"),
        "actual": summary.get("total_actual"),
        "variance_amount": summary.get("variance_amount"),
        "variance_pct": summary.get("variance_pct"),
        "largest_miss_category": summary.get("largest_miss_category"),
        "largest_miss_variance_pct": summary.get("largest_miss_variance_pct"),
        "largest_contributing_region": summary.get("largest_state"),
        "forecast_vs_target": None,
        "relevant_festivals": (festival or {}).get("payload", {}).get("rows", []),
        "anomaly_signals": (anomaly or {}).get("payload", {}).get("anomalies", [])[:5],
        "supporting_query_ids": [
            qid
            for r in results
            for qid in [
                r.get("payload", {}).get("provenance", {}).get("query_id"),
                r.get("payload", {}).get("query_id"),
            ]
            if qid
        ],
        "region_breakdown": (region or {}).get("payload", {}).get("rows", [])[:5],
        "notes": [
            "Anomaly flags indicate statistical outliers, not proven causes.",
            "Festival dates are contextual associations only.",
        ],
    }

    if forecast and summary.get("by_category"):
        forecast_payload = forecast.get("payload", {})
        category = forecast_payload.get("category")
        by_category = summary.get("by_category", [])
        cat_row = next(
            (row for row in by_category if row.get("category") == category),
            None,
        )
        forecast_total = forecast_payload.get("forecast_total")
        if cat_row and forecast_total is not None:
            category_target = float(cat_row["target_amount"])
            bundle["forecast_vs_target"] = {
                "grain": "category",
                "category": category,
                "forecast_total": forecast_total,
                "target_total": round(category_target, 2),
                "delta": round(float(forecast_total) - category_target, 2),
                "model": forecast_payload.get("model_name"),
                "horizon_days": forecast_payload.get("horizon_days"),
                "is_experimental": forecast_payload.get("is_experimental", False),
                "comparison_note": (
                    f"{category} category forecast compared to {category} category target "
                    f"for {state.get('target_month')}."
                ),
            }

    return bundle


def format_report(evidence: dict[str, Any]) -> str:
    """Deterministic report formatter — every number cites a query/tool id."""
    qids = ", ".join(evidence.get("supporting_query_ids") or [])
    lines = [
        f"Investigation: {evidence.get('question')}",
        f"Period: {evidence.get('target_month')}",
        "",
        "## Target vs Actual",
        f"- Target: ₹{evidence.get('target')} [source: variance tool]",
        f"- Actual: ₹{evidence.get('actual')} [source: variance tool]",
        f"- Variance: ₹{evidence.get('variance_amount')} ({evidence.get('variance_pct')}%) [source: variance tool]",
        "",
        "## Largest Contributing Factors",
        f"- Largest miss category: {evidence.get('largest_miss_category')} "
        f"({evidence.get('largest_miss_variance_pct')}%) [source: variance tool]",
        f"- Largest contributing region (by category drill-down): "
        f"{evidence.get('largest_contributing_region')} [source: variance tool]",
    ]

    fvt = evidence.get("forecast_vs_target")
    if fvt:
        exp = " (experimental horizon)" if fvt.get("is_experimental") else ""
        category = fvt.get("category", "category")
        lines.extend(
            [
                "",
                "## Forecast vs Target (same category grain)",
                f"- Category: {category} [source: forecast + variance tools]",
                f"- {category} forecast total ({fvt.get('model')}, {fvt.get('horizon_days')}-day): "
                f"₹{fvt.get('forecast_total')}{exp} [source: forecast tool]",
                f"- {category} target total: ₹{fvt.get('target_total')} [source: variance tool]",
                f"- Delta ({category} forecast − {category} target): ₹{fvt.get('delta')} "
                f"[source: forecast + variance tools]",
            ]
        )
        if fvt.get("comparison_note"):
            lines.append(f"- Note: {fvt['comparison_note']}")

    festivals = evidence.get("relevant_festivals") or []
    if festivals:
        names = ", ".join(f["festival_name"] for f in festivals[:3])
        lines.extend(
            [
                "",
                "## Festival Context (association only)",
                f"- Festivals in period: {names} [source: Q_festivals_in_range]",
            ]
        )

    anomalies = evidence.get("anomaly_signals") or []
    if anomalies:
        lines.extend(
            [
                "",
                "## Anomaly Signals (not causal proof)",
                f"- {len(anomalies)} flagged outlier(s) in window [source: anomaly_check tool]",
            ]
        )

    lines.extend(["", "## Supporting Evidence IDs", f"- {qids}"])
    for note in evidence.get("notes", []):
        lines.append(f"- Note: {note}")

    return "\n".join(lines)
