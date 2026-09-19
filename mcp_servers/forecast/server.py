"""MCP server: forecast."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mcp.server.mcpserver import MCPServer

from backend.app.tools.handlers import ForecastInput, handle_forecast

mcp = MCPServer("marketlens-forecast")


@mcp.tool(name="forecast", description="Return demand forecast for category and horizon")
def forecast(category: str, horizon_days: int, model_name: str = "xgboost") -> str:
    result = handle_forecast(
        ForecastInput(category=category, horizon_days=horizon_days, model_name=model_name)
    )
    return json.dumps(result, default=str)


if __name__ == "__main__":
    mcp.run()
