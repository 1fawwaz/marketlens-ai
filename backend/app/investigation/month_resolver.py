"""Investigation month resolution with explicit, inferred, and contextual fallbacks."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from backend.app.ml.variance import get_variance

logger = logging.getLogger(__name__)

RESOLVER_VERSION = "2026-03-19-context-fallback-v2"
RESOLVER_MODULE = __file__


@dataclass
class MonthResolution:
    target_month: str
    mode: str
    requested_variance_pct: float | None = None
    matched_variance_pct: float | None = None


_MONTH_ALIASES = {
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sep": 9,
    "sept": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
}


def _monthly_summaries() -> list[dict]:
    rows = get_variance()
    by_month: dict[str, dict] = {}
    for row in rows:
        month = str(row["target_month"])
        bucket = by_month.setdefault(
            month,
            {"target_month": month, "total_target": 0.0, "total_actual": 0.0},
        )
        bucket["total_target"] += float(row["target_amount"])
        bucket["total_actual"] += float(row["actual_amount"])
    summaries = []
    for month, bucket in by_month.items():
        target = bucket["total_target"]
        actual = bucket["total_actual"]
        variance_pct = ((actual - target) / target * 100) if target else 0.0
        summaries.append(
            {
                "target_month": month,
                "variance_pct": round(variance_pct, 4),
            }
        )
    return summaries


def _variance_pct_for_month(month: str) -> float | None:
    return next(
        (s["variance_pct"] for s in _monthly_summaries() if s["target_month"] == month),
        None,
    )


def _canonical_month(year: int, month_num: int) -> str:
    return f"{year:04d}-{month_num:02d}-01"


def _normalize_context_month(context_month: str | None) -> str | None:
    if not context_month:
        return None
    value = context_month.strip()
    if not value:
        return None
    explicit = re.match(r"^(\d{4}-\d{2}-\d{2})", value)
    if explicit:
        return explicit.group(1)
    year_month = re.match(r"^(\d{4})-(\d{2})$", value)
    if year_month:
        return _canonical_month(int(year_month.group(1)), int(year_month.group(2)))
    return None


def _latest_dataset_month() -> str:
    summaries = _monthly_summaries()
    if not summaries:
        raise ValueError("No variance snapshots available in dataset.")
    return max(s["target_month"] for s in summaries)


def _match_known_month(month: str) -> MonthResolution | None:
    summaries = _monthly_summaries()
    if not any(s["target_month"] == month for s in summaries):
        return None
    return MonthResolution(
        target_month=month,
        mode="explicit_date",
        matched_variance_pct=_variance_pct_for_month(month),
    )


def _resolve_named_month(question: str) -> MonthResolution | None:
    pattern = (
        r"\b("
        + "|".join(sorted(_MONTH_ALIASES, key=len, reverse=True))
        + r")\b[\s,]+(\d{4})\b"
    )
    match = re.search(pattern, question, flags=re.IGNORECASE)
    if not match:
        return None
    month_num = _MONTH_ALIASES[match.group(1).lower()]
    year = int(match.group(2))
    return _match_known_month(_canonical_month(year, month_num))


def _resolve_year_month(question: str) -> MonthResolution | None:
    match = re.search(r"\b(\d{4})-(\d{2})(?:-\d{2})?\b", question)
    if not match:
        return None
    year = int(match.group(1))
    month_num = int(match.group(2))
    if month_num < 1 or month_num > 12:
        return None
    return _match_known_month(_canonical_month(year, month_num))


def _resolve_context_fallback(context_month: str | None) -> MonthResolution:
    normalized = _normalize_context_month(context_month)
    if normalized:
        matched = _match_known_month(normalized)
        if matched:
            return MonthResolution(
                target_month=matched.target_month,
                mode="dashboard_context",
                matched_variance_pct=matched.matched_variance_pct,
            )

    latest = _latest_dataset_month()
    return MonthResolution(
        target_month=latest,
        mode="latest_available",
        matched_variance_pct=_variance_pct_for_month(latest),
    )


def resolve_target_month(
    question: str,
    context_month: str | None = None,
) -> MonthResolution:
    """Resolve investigation month from the question, then dashboard context, then latest data."""
    logger.info(
        "month_resolver.start version=%s question_len=%d context_month=%s",
        RESOLVER_VERSION,
        len(question),
        context_month or "(none)",
    )

    explicit = re.search(r"(\d{4}-\d{2}-\d{2})", question)
    if explicit:
        month = explicit.group(1)
        resolution = MonthResolution(
            target_month=month,
            mode="explicit_date",
            matched_variance_pct=_variance_pct_for_month(month),
        )
        logger.info(
            "month_resolver.branch=explicit_date target_month=%s",
            resolution.target_month,
        )
        return resolution

    named = _resolve_named_month(question)
    if named:
        logger.info(
            "month_resolver.branch=named_month target_month=%s",
            named.target_month,
        )
        return named

    year_month = _resolve_year_month(question)
    if year_month:
        logger.info(
            "month_resolver.branch=year_month target_month=%s",
            year_month.target_month,
        )
        return year_month

    percent_match = re.search(r"(\d+(?:\.\d+)?)\s*%", question.lower())
    if percent_match:
        requested = float(percent_match.group(1))
        target_variance = -requested
        summaries = _monthly_summaries()
        if not summaries:
            raise ValueError("No variance snapshots available for percent matching")
        best = min(summaries, key=lambda s: abs(s["variance_pct"] - target_variance))
        resolution = MonthResolution(
            target_month=best["target_month"],
            mode="percent_match",
            requested_variance_pct=requested,
            matched_variance_pct=best["variance_pct"],
        )
        logger.info(
            "month_resolver.branch=percent_match target_month=%s requested=%s",
            resolution.target_month,
            requested,
        )
        return resolution

    auto_hint = re.search(
        r"\b(auto|automatic|worst month|largest miss)\b",
        question.lower(),
    )
    if auto_hint:
        summaries = _monthly_summaries()
        worst = min(summaries, key=lambda s: s["variance_pct"])
        resolution = MonthResolution(
            target_month=worst["target_month"],
            mode="auto_worst_month",
            matched_variance_pct=worst["variance_pct"],
        )
        logger.info(
            "month_resolver.branch=auto_worst_month target_month=%s",
            resolution.target_month,
        )
        return resolution

    resolution = _resolve_context_fallback(context_month)
    logger.info(
        "month_resolver.branch=%s target_month=%s",
        resolution.mode,
        resolution.target_month,
    )
    return resolution
