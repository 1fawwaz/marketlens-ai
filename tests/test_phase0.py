"""Phase 0 data-quality and ETL validation tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from db import get_engine  # noqa: E402
from etl.load_data import (  # noqa: E402
    load_festival_calendar,
    load_order_details,
    load_orders,
    load_sales_targets,
    run_etl,
)

RAW_DIR = PROJECT_ROOT / "data" / "raw"


# ---------------------------------------------------------------------------
# Raw CSV validation (no DB required)
# ---------------------------------------------------------------------------


class TestRawCsvFiles:
    def test_expected_files_exist(self):
        expected = ["List of Orders.csv", "Order Details.csv", "Sales target.csv"]
        for name in expected:
            assert (RAW_DIR / name).exists(), f"Missing {name}"

    def test_orders_row_counts(self):
        raw = pd.read_csv(RAW_DIR / "List of Orders.csv")
        assert len(raw) == 560
        orders = load_orders()
        assert len(orders) == 500

    def test_order_details_row_count(self):
        details = load_order_details()
        assert len(details) == 1500

    def test_sales_targets_grain(self):
        targets = load_sales_targets()
        assert len(targets) == 36
        assert targets.duplicated(subset=["category", "target_month"]).sum() == 0

    def test_no_nulls_in_cleaned_orders(self):
        orders = load_orders()
        assert orders.isnull().sum().sum() == 0

    def test_no_nulls_in_order_details(self):
        details = load_order_details()
        assert details.isnull().sum().sum() == 0

    def test_kerala_state_trimmed_in_etl(self):
        orders = load_orders()
        assert "Kerala " not in orders["customer_state"].unique()
        assert "Kerala" in orders["customer_state"].unique()

    def test_date_range(self):
        orders = load_orders()
        assert orders["order_date"].min().date().isoformat() == "2018-04-01"
        assert orders["order_date"].max().date().isoformat() == "2019-03-31"

    def test_categories_match_between_details_and_targets(self):
        details = load_order_details()
        targets = load_sales_targets()
        assert set(details["category"]) == set(targets["category"])

    def test_join_integrity_orders_to_details(self):
        orders = load_orders()
        details = load_order_details()
        order_ids = set(orders["order_id"])
        detail_ids = set(details["order_id"])
        assert detail_ids.issubset(order_ids)
        assert len(detail_ids - order_ids) == 0
        assert len(order_ids - detail_ids) == 0

    def test_festival_calendar_covers_sales_range(self):
        orders = load_orders()
        festivals = load_festival_calendar()
        min_date = orders["order_date"].min().date()
        max_date = orders["order_date"].max().date()
        fest_min = festivals["festival_date"].min()
        fest_max = festivals["festival_date"].max()
        # Calendar should overlap the sales window (not necessarily start on day 1)
        assert fest_min <= max_date
        assert fest_max >= min_date
        assert len(festivals) == 18


# ---------------------------------------------------------------------------
# PostgreSQL validation (requires running DB)
# ---------------------------------------------------------------------------


def _db_available() -> bool:
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


pytestmark_db = pytest.mark.skipif(not _db_available(), reason="PostgreSQL not available")


@pytest.fixture(scope="module")
def loaded_db():
    if not _db_available():
        pytest.skip("PostgreSQL not available")
    counts = run_etl(truncate=True)
    return counts


@pytestmark_db
class TestPostgresEtl:
    def test_etl_row_counts(self, loaded_db):
        assert loaded_db == {
            "orders": 500,
            "order_details": 1500,
            "sales_targets": 36,
            "festival_calendar": 18,
        }

    def test_etl_idempotent(self, loaded_db):
        second = run_etl(truncate=True)
        assert second == loaded_db

    def test_foreign_key_integrity(self, loaded_db):
        engine = get_engine()
        with engine.connect() as conn:
            orphan = conn.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM order_details d
                    LEFT JOIN orders o ON d.order_id = o.order_id
                    WHERE o.order_id IS NULL
                    """
                )
            ).scalar()
            assert orphan == 0

    def test_sales_target_unique_grain(self, loaded_db):
        engine = get_engine()
        with engine.connect() as conn:
            dupes = conn.execute(
                text(
                    """
                    SELECT category, target_month, COUNT(*)
                    FROM sales_targets
                    GROUP BY category, target_month
                    HAVING COUNT(*) > 1
                    """
                )
            ).fetchall()
            assert dupes == []

    def test_actual_sales_joinable_to_targets(self, loaded_db):
        engine = get_engine()
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT COUNT(*) FROM (
                        SELECT DISTINCT d.category,
                               DATE_TRUNC('month', o.order_date)::date AS month_start
                        FROM order_details d
                        JOIN orders o ON d.order_id = o.order_id
                    ) actual
                    LEFT JOIN sales_targets t
                      ON actual.category = t.category
                     AND actual.month_start = t.target_month
                    WHERE t.target_id IS NULL
                    """
                )
            ).scalar()
            assert rows == 0

    def test_festival_calendar_in_db(self, loaded_db):
        engine = get_engine()
        with engine.connect() as conn:
            count = conn.execute(text("SELECT COUNT(*) FROM festival_calendar")).scalar()
            assert count == 18

    def test_etl_run_log_written(self, loaded_db):
        engine = get_engine()
        with engine.connect() as conn:
            count = conn.execute(
                text(
                    "SELECT COUNT(*) FROM etl_run_log WHERE pipeline_name = 'raw_csv_to_postgres'"
                )
            ).scalar()
            assert count >= 1
