"""MCP server: variance."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mcp.server.mcpserver import MCPServer

from backend.app.tools.handlers import VarianceInput, handle_variance

mcp = MCPServer("marketlens-variance")


@mcp.tool(name="variance", description="Return target vs actual variance analysis")
def variance(target_month: str, category: str | None = None) -> str:
    result = handle_variance(VarianceInput(target_month=target_month, category=category))
    return json.dumps(result, default=str)


if __name__ == "__main__":
    mcp.run()
