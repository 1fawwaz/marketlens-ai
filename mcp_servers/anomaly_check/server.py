"""MCP server: anomaly_check."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mcp.server.mcpserver import MCPServer

from backend.app.tools.handlers import AnomalyInput, handle_anomaly_check

mcp = MCPServer("marketlens-anomaly-check")


@mcp.tool(name="anomaly_check", description="Return flagged revenue anomalies")
def anomaly_check(
    dimension_type: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> str:
    result = handle_anomaly_check(
        AnomalyInput(
            dimension_type=dimension_type,
            start_date=start_date,
            end_date=end_date,
        )
    )
    return json.dumps(result, default=str)


if __name__ == "__main__":
    mcp.run()
