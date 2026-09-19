"""Month resolution tests."""

from __future__ import annotations

import pytest

from backend.app.investigation.month_resolver import (
    RESOLVER_VERSION,
    resolve_target_month,
)


@pytest.mark.parametrize(
    "question,expected_month,expected_mode",
    [
        (
            "We missed the sales target by 12%. What factors contributed to the gap?",
            "2019-02-01",
            "percent_match",
        ),
        (
            "Investigate target miss for 2018-11-01",
            "2018-11-01",
            "explicit_date",
        ),
        (
            "Run automatic investigation for worst month",
            "2018-07-01",
            "auto_worst_month",
        ),
        (
            "Why did we miss the February 2019 sales target, and what are the biggest factors contributing to the gap?",
            "2019-02-01",
            "explicit_date",
        ),
        (
            "Investigate the July 2018 shortfall",
            "2018-07-01",
            "explicit_date",
        ),
        (
            "Why did we miss the February 2019 sales target?",
            "2019-02-01",
            "explicit_date",
        ),
        (
            "Show variance for 2019-02",
            "2019-02-01",
            "explicit_date",
        ),
    ],
)
def test_resolve_target_month(question, expected_month, expected_mode):
    resolution = resolve_target_month(question)
    assert resolution.target_month == expected_month
    assert resolution.mode == expected_mode


def test_percent_match_not_worst_month():
    resolution = resolve_target_month("We missed the sales target by 12%. Why?")
    assert resolution.target_month != "2018-07-01"


def test_no_month_uses_dashboard_context():
    resolution = resolve_target_month(
        "Which category contributed most to the sales shortfall?",
        context_month="2019-02",
    )
    assert resolution.target_month == "2019-02-01"
    assert resolution.mode == "dashboard_context"


def test_no_month_uses_latest_available_without_context():
    resolution = resolve_target_month("Why did we miss the target?")
    assert resolution.mode == "latest_available"
    assert resolution.target_month.endswith("-01")


def test_resolver_version_bumped():
    assert "context-fallback-v2" in RESOLVER_VERSION
