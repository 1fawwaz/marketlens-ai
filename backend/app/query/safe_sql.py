"""Safe parameterized SQL query builder — no arbitrary LLM SQL."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import text

from backend.app.database import get_engine


class QueryTemplate(str, Enum):
    MONTHLY_REVENUE_BY_CATEGORY = "monthly_revenue_by_category"
    REVENUE_BY_STATE = "revenue_by_state"
    TOP_SUBCATEGORIES = "top_subcategories"
    ORDER_VOLUME_BY_DATE = "order_volume_by_date"
    FESTIVALS_IN_RANGE = "festivals_in_range"


class SqlQuerySpec(BaseModel):
    template: QueryTemplate
    start_date: str | None = None
    end_date: str | None = None
    category: str | None = None
    customer_state: str | None = None
    limit: int = Field(default=100, ge=1, le=500)

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str | None) -> str | None:
        if v is not None and v not in {"Clothing", "Electronics", "Furniture"}:
            raise ValueError("Invalid category")
        return v


TEMPLATES: dict[QueryTemplate, tuple[str, list[str]]] = {
    QueryTemplate.MONTHLY_REVENUE_BY_CATEGORY: (
        """
        SELECT DATE_TRUNC('month', o.order_date)::date AS month_start,
               d.category,
               SUM(d.amount) AS revenue,
               SUM(d.profit) AS profit
        FROM orders o
        JOIN order_details d ON o.order_id = d.order_id
        WHERE (:start_date IS NULL OR o.order_date >= :start_date)
          AND (:end_date IS NULL OR o.order_date <= :end_date)
          AND (:category IS NULL OR d.category = :category)
        GROUP BY 1, 2
        ORDER BY 1, 2
        LIMIT :limit
        """,
        ["start_date", "end_date", "category", "limit"],
    ),
    QueryTemplate.REVENUE_BY_STATE: (
        """
        SELECT o.customer_state,
               SUM(d.amount) AS revenue,
               COUNT(DISTINCT o.order_id) AS order_count
        FROM orders o
        JOIN order_details d ON o.order_id = d.order_id
        WHERE (:start_date IS NULL OR o.order_date >= :start_date)
          AND (:end_date IS NULL OR o.order_date <= :end_date)
          AND (:category IS NULL OR d.category = :category)
        GROUP BY o.customer_state
        ORDER BY revenue DESC
        LIMIT :limit
        """,
        ["start_date", "end_date", "category", "limit"],
    ),
    QueryTemplate.TOP_SUBCATEGORIES: (
        """
        SELECT d.category, d.sub_category,
               SUM(d.amount) AS revenue
        FROM orders o
        JOIN order_details d ON o.order_id = d.order_id
        WHERE (:start_date IS NULL OR o.order_date >= :start_date)
          AND (:end_date IS NULL OR o.order_date <= :end_date)
          AND (:category IS NULL OR d.category = :category)
        GROUP BY d.category, d.sub_category
        ORDER BY revenue DESC
        LIMIT :limit
        """,
        ["start_date", "end_date", "category", "limit"],
    ),
    QueryTemplate.ORDER_VOLUME_BY_DATE: (
        """
        SELECT o.order_date,
               COUNT(DISTINCT o.order_id) AS orders,
               SUM(d.amount) AS revenue
        FROM orders o
        JOIN order_details d ON o.order_id = d.order_id
        WHERE (:start_date IS NULL OR o.order_date >= :start_date)
          AND (:end_date IS NULL OR o.order_date <= :end_date)
        GROUP BY o.order_date
        ORDER BY o.order_date
        LIMIT :limit
        """,
        ["start_date", "end_date", "limit"],
    ),
    QueryTemplate.FESTIVALS_IN_RANGE: (
        """
        SELECT festival_date, festival_name, region_scope
        FROM festival_calendar
        WHERE (:start_date IS NULL OR festival_date >= :start_date)
          AND (:end_date IS NULL OR festival_date <= :end_date)
        ORDER BY festival_date
        LIMIT :limit
        """,
        ["start_date", "end_date", "limit"],
    ),
}


def execute_safe_query(spec: SqlQuerySpec) -> dict[str, Any]:
    sql, allowed = TEMPLATES[spec.template]
    params = {k: getattr(spec, k) for k in allowed}
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(text(sql), params).mappings().all()
    serialized = []
    for row in rows:
        item = {}
        for k, v in dict(row).items():
            item[k] = v.isoformat() if hasattr(v, "isoformat") else v
        serialized.append(item)
    return {
        "template": spec.template.value,
        "query_id": f"Q_{spec.template.value}",
        "row_count": len(serialized),
        "rows": serialized,
        "provenance": {
            "source": "postgresql",
            "method": "parameterized_template",
            "template": spec.template.value,
        },
    }
