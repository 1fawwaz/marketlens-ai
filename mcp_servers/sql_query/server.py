"""MCP server: sql_query — safe parameterized SQL templates."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mcp.server.mcpserver import MCPServer

from backend.app.query.safe_sql import QueryTemplate, SqlQuerySpec, execute_safe_query

mcp = MCPServer("marketlens-sql-query")


@mcp.tool(name="sql_query", description="Execute safe parameterized SQL template")
def sql_query(
    template: str,
    start_date: str | None = None,
    end_date: str | None = None,
    category: str | None = None,
    customer_state: str | None = None,
    limit: int = 100,
) -> str:
    spec = SqlQuerySpec(
        template=QueryTemplate(template),
        start_date=start_date,
        end_date=end_date,
        category=category,
        customer_state=customer_state,
        limit=limit,
    )
    return json.dumps(execute_safe_query(spec), default=str)


if __name__ == "__main__":
    mcp.run()
